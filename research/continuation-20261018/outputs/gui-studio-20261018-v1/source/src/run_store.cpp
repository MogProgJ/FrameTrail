#include "frametrail/run_store.hpp"
#include <sqlite3.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <limits>
#include <sstream>
#include <iomanip>
#include <locale>
#include <stdexcept>

namespace frametrail {
namespace {
constexpr int application_id = 0x4654524c; // FTRL
std::string utf8(const std::filesystem::path& path) {
    const auto value = path.u8string(); return {value.begin(), value.end()};
}
std::filesystem::path path_from(const std::string& value) {
    return std::filesystem::path(std::u8string(value.begin(),value.end()));
}
std::int64_t integer(std::uint64_t value) {
    if (value > std::uint64_t(std::numeric_limits<std::int64_t>::max()))
        throw std::invalid_argument("Saved run integer exceeds SQLite range");
    return static_cast<std::int64_t>(value);
}
std::FILE* exclusive_file(const std::filesystem::path& path) {
    std::FILE* file{};
#ifdef _WIN32
    _wfopen_s(&file,path.c_str(),L"wbx");
#else
    file = std::fopen(path.c_str(),"wbx");
#endif
    if (!file) throw std::runtime_error("Cannot create output; choose a new file in a writable folder: " + utf8(path));
    return file;
}
std::string quote(std::string_view value) {
    std::string out{"\""};
    for (const auto c : value) { out += c; if (c == '"') out += '"'; }
    return out + '"';
}
struct Statement {
    sqlite3_stmt* value{};
    sqlite3* database{};
    Statement(sqlite3* db,const char* sql) : database(db) {
        if (sqlite3_prepare_v2(db,sql,-1,&value,nullptr) != SQLITE_OK)
            throw std::runtime_error(std::string("Read saved run: ")+sqlite3_errmsg(db));
    }
    ~Statement() { sqlite3_finalize(value); }
    Statement(const Statement&) = delete;
    void check(int result) const {
        if (result != SQLITE_OK) throw std::runtime_error(sqlite3_errmsg(database));
    }
    void text(int index,std::string_view text) { check(sqlite3_bind_text(value,index,text.empty() ? "" : text.data(),int(text.size()),SQLITE_TRANSIENT)); }
    void number(int index,std::int64_t number) { check(sqlite3_bind_int64(value,index,number)); }
    void real(int index,double number) { check(sqlite3_bind_double(value,index,number)); }
    void time(int index,std::optional<std::chrono::microseconds> time) {
        if (time) number(index,time->count()); else check(sqlite3_bind_null(value,index));
    }
    bool row() {
        const auto result=sqlite3_step(value);
        if (result==SQLITE_ROW) return true;
        if (result==SQLITE_DONE) return false;
        throw std::runtime_error(std::string("Saved run operation: ")+sqlite3_errmsg(database));
    }
    std::string text(int column) const {
        const auto* data=sqlite3_column_text(value,column);
        return data ? std::string(reinterpret_cast<const char*>(data),sqlite3_column_bytes(value,column)) : std::string{};
    }
    std::int64_t number(int column) const { return sqlite3_column_int64(value,column); }
    double real(int column) const { return sqlite3_column_double(value,column); }
    std::optional<std::chrono::microseconds> time(int column) const {
        if (sqlite3_column_type(value,column)==SQLITE_NULL) return {};
        return std::chrono::microseconds(number(column));
    }
};
std::vector<std::uint8_t> thumbnail(const Frame& frame) {
    if (frame.width<=0 || frame.height<=0 || frame.width>std::numeric_limits<int>::max()/3 || frame.stride<frame.width*3 ||
        frame.pixels.size()<std::size_t(frame.stride)*frame.height)
        throw std::invalid_argument("Cannot save thumbnail from invalid frame");
    const double scale=std::min({1.0,160.0/frame.width,90.0/frame.height});
    const int width=std::max(1,int(frame.width*scale)),height=std::max(1,int(frame.height*scale));
    const auto header="P6\n"+std::to_string(width)+" "+std::to_string(height)+"\n255\n";
    std::vector<std::uint8_t> out(header.begin(),header.end()); out.reserve(out.size()+width*height*3);
    for(int y=0;y<height;++y) for(int x=0;x<width;++x) {
        const auto offset=std::size_t(std::int64_t(y)*frame.height/height)*frame.stride+std::size_t(std::int64_t(x)*frame.width/width)*3;
        out.insert(out.end(),frame.pixels.begin()+offset,frame.pixels.begin()+offset+3);
    }
    return out;
}
CrossingEvent event_from(const Statement& row) {
    CrossingEvent event;
    event.id=row.number(0); event.track_id=row.number(1); event.sequence=row.number(2);
    event.timestamp=row.time(3); event.class_id=int(row.number(4));
    event.direction=static_cast<CrossingDirection>(row.number(5));
    event.position={row.real(6),row.real(7)}; return event;
}
bool same_event(const CrossingEvent& a,const CrossingEvent& b) {
    return a.id==b.id && a.track_id==b.track_id && a.sequence==b.sequence && a.timestamp==b.timestamp &&
        a.class_id==b.class_id && a.direction==b.direction && a.position.x==b.position.x && a.position.y==b.position.y;
}
}

FileStamp file_stamp(const std::filesystem::path& path) {
    if (!std::filesystem::is_regular_file(path)) throw std::runtime_error("Source or model file is missing: "+utf8(path));
    return {std::filesystem::file_size(path),std::filesystem::last_write_time(path).time_since_epoch().count()};
}
struct RunStore::Impl {
    sqlite3* database{};
    bool writable{};
    int schema_version{4};
    DetectorModel variant{DetectorModel::nano};
    bool execution_metadata{};
    bool association_metadata{};
    std::optional<ExecutionInfo> last_execution;
    explicit Impl(const std::filesystem::path& path,bool write) : writable(write) {
        const auto name=utf8(std::filesystem::absolute(path));
        const auto result=sqlite3_open_v2(name.c_str(),&database,
            (write ? SQLITE_OPEN_READWRITE : SQLITE_OPEN_READONLY)|SQLITE_OPEN_NOMUTEX,nullptr);
        if(result!=SQLITE_OK) {
            const auto error=database ? std::string(sqlite3_errmsg(database)) : "Out of memory";
            sqlite3_close(database); database=nullptr; throw std::runtime_error("Open saved run: "+error);
        }
        sqlite3_busy_timeout(database,1500);
        sqlite3_limit(database,SQLITE_LIMIT_LENGTH,1024*1024);
        sqlite3_db_config(database,SQLITE_DBCONFIG_DEFENSIVE,1,nullptr);
    }
    ~Impl() { sqlite3_close(database); }
    void execute(const char* sql) {
        if(sqlite3_exec(database,sql,nullptr,nullptr,nullptr)!=SQLITE_OK)
            throw std::runtime_error(std::string("Saved run operation: ")+sqlite3_errmsg(database));
    }
    void require_writer() const {
        if (!writable) throw std::logic_error("Saved review is read-only");
        Statement row(database,"SELECT status FROM run WHERE id=1");
        if(!row.row() || row.text(0)!="running") throw std::logic_error("Run is already finished");
    }
};
RunStore::RunStore(std::unique_ptr<Impl> impl):impl_(std::move(impl)) {}
RunStore::~RunStore()=default;
RunStore::RunStore(RunStore&&) noexcept=default;
RunStore& RunStore::operator=(RunStore&&) noexcept=default;

RunStore RunStore::create(const std::filesystem::path& database,const RunConfiguration& config,const MediaInfo& media) {
    if(config.kind!=RunKind::crossings && config.kind!=RunKind::appearances)throw std::invalid_argument("Unsupported analysis kind");
    if(config.kind==RunKind::crossings && !config.tracking.line) throw std::invalid_argument("Saved crossing analysis requires a counting line");
    const auto source=std::filesystem::absolute(config.source), model=std::filesystem::absolute(config.detector.model);
    const auto source_stamp=file_stamp(source),model_stamp=file_stamp(model);
    // Validate native model/tracker settings before creating any output.
    Tracker validation(config.tracking);
    for(const auto id:config.tracking.classes)if(!model_has_class(config.detector.variant,id))throw std::invalid_argument("Tracking category is not supported by this model");
    if(!std::isfinite(config.detector.confidence) || config.detector.confidence<=0 || config.detector.confidence>1 ||
        !std::isfinite(config.detector.nms_iou) || config.detector.nms_iou<=0 || config.detector.nms_iou>1)
        throw std::invalid_argument("Invalid detector thresholds");
    auto* reservation=exclusive_file(database);
    if(std::fclose(reservation)!=0) throw std::runtime_error("Cannot close new saved run file");
    struct NewFileGuard {
        std::filesystem::path path;
        bool ready{};
        ~NewFileGuard() {if(!ready){std::error_code ignored;std::filesystem::remove(path,ignored);}}
    } guard{database};
    auto impl=std::make_unique<Impl>(database,true);impl->variant=config.detector.variant;
    impl->execute("PRAGMA application_id=1179931212; PRAGMA user_version=4; PRAGMA trusted_schema=OFF; PRAGMA foreign_keys=ON;");
    impl->execute("BEGIN IMMEDIATE");
    impl->execute("CREATE TABLE run(id INTEGER PRIMARY KEY CHECK(id=1),created TEXT NOT NULL,status TEXT NOT NULL,"
        "error TEXT NOT NULL DEFAULT '',source TEXT NOT NULL,source_bytes INTEGER NOT NULL,source_modified INTEGER NOT NULL,"
        "model TEXT NOT NULL,model_bytes INTEGER NOT NULL,model_modified INTEGER NOT NULL,confidence REAL NOT NULL,nms REAL NOT NULL,"
        "classes TEXT NOT NULL,ax REAL NOT NULL,ay REAL NOT NULL,bx REAL NOT NULL,by REAL NOT NULL,direction INTEGER NOT NULL,"
        "deadband REAL NOT NULL,rearm REAL NOT NULL,codec TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,"
        "duration_us INTEGER,processed_frames INTEGER NOT NULL DEFAULT 0,last_timestamp_us INTEGER,timestamp_seekable INTEGER NOT NULL DEFAULT 1,"
        "run_id TEXT NOT NULL DEFAULT(lower(hex(randomblob(16)))),"
        "model_type TEXT NOT NULL CHECK(model_type IN('nano','small','world-s','world-m','openimages','rfdetr-7758628')),"
        "run_kind TEXT NOT NULL CHECK(run_kind IN('crossings','appearances')),"
        "engine TEXT NOT NULL DEFAULT 'FrameTrail 0.12 / recognition-v1 + YOLOX / tracker-v2 / scene-guard-v1',"
        "association_policy TEXT NOT NULL DEFAULT 'greedy',"
        "vocabulary_id TEXT NOT NULL DEFAULT 'coco-v1',vocabulary TEXT NOT NULL DEFAULT '',"
        "requested_backend TEXT NOT NULL DEFAULT 'cpu',gpu_device INTEGER NOT NULL DEFAULT -1,"
        "execution_backend TEXT NOT NULL DEFAULT 'CPU',execution_runtime TEXT NOT NULL DEFAULT '',"
        "execution_device TEXT NOT NULL DEFAULT '',execution_fallback TEXT NOT NULL DEFAULT '');"
        "CREATE TABLE events(id INTEGER PRIMARY KEY CHECK(id>0),track_id INTEGER NOT NULL,sequence INTEGER NOT NULL,"
        "timestamp_us INTEGER,class_id INTEGER NOT NULL,direction INTEGER NOT NULL CHECK(direction IN(1,2)),"
        "x REAL NOT NULL,y REAL NOT NULL,thumbnail BLOB NOT NULL);"
        "CREATE TABLE appearances(id INTEGER PRIMARY KEY CHECK(id>0),class_id INTEGER NOT NULL CHECK(class_id BETWEEN 0 AND 614),"
        "first_sequence INTEGER NOT NULL,last_sequence INTEGER NOT NULL,first_timestamp_us INTEGER,last_timestamp_us INTEGER,"
        "observations INTEGER NOT NULL CHECK(observations>0),first_confidence REAL NOT NULL,peak_confidence REAL NOT NULL,"
        "left REAL NOT NULL,top REAL NOT NULL,right REAL NOT NULL,bottom REAL NOT NULL,thumbnail BLOB NOT NULL);");
    Statement insert(impl->database,"INSERT INTO run(id,created,status,source,source_bytes,source_modified,model,model_bytes,model_modified,"
        "confidence,nms,classes,ax,ay,bx,by,direction,deadband,rearm,codec,width,height,duration_us,model_type,run_kind)"
        " VALUES(1,strftime('%Y-%m-%dT%H:%M:%fZ','now'),'running',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
    insert.text(1,utf8(source)); insert.number(2,integer(source_stamp.bytes)); insert.number(3,source_stamp.modified);
    insert.text(4,utf8(model)); insert.number(5,integer(model_stamp.bytes)); insert.number(6,model_stamp.modified);
    insert.real(7,config.detector.confidence);insert.real(8,config.detector.nms_iou);
    std::string classes;for(auto id:config.tracking.classes) { if(!classes.empty())classes+=',';classes+=std::to_string(id); }
    insert.text(9,classes); const auto line=config.tracking.line.value_or(CountingLine{});
    insert.real(10,line.a.x);insert.real(11,line.a.y);insert.real(12,line.b.x);insert.real(13,line.b.y);
    insert.number(14,static_cast<int>(line.direction));insert.real(15,line.deadband);insert.real(16,line.rearm_distance);
    insert.text(17,media.codec);insert.number(18,media.width);insert.number(19,media.height);insert.time(20,media.duration);
    insert.text(21,std::string(model_id(config.detector.variant)));
    insert.text(22,config.kind==RunKind::appearances ? "appearances" : "crossings");
    insert.row();
    Statement backend(impl->database,"UPDATE run SET requested_backend=?,gpu_device=?,association_policy=?,vocabulary_id=?,vocabulary=? WHERE id=1");
    backend.text(1,backend_id(config.detector.backend));backend.number(2,config.detector.gpu_device);backend.text(3,association_name(config.tracking.association));
    backend.text(4,std::string(model_id(config.detector.variant)));
    const auto vocabulary=model_vocabulary(config.detector.variant);
    backend.text(5,vocabulary);backend.row();
    impl->execute("COMMIT");impl->execution_metadata=true;impl->association_metadata=true;guard.ready=true;return RunStore(std::move(impl));
}
RunStore::RunStore(const std::filesystem::path& database):impl_(std::make_unique<Impl>(database,false)) {
    impl_->execute("PRAGMA trusted_schema=OFF");
    Statement app(impl_->database,"PRAGMA application_id"),version(impl_->database,"PRAGMA user_version");
    if(!app.row() || app.number(0)!=application_id || !version.row() || (version.number(0)<1 || version.number(0)>4))
        throw std::runtime_error("This is not a supported FrameTrail run (schema versions 1–4)");
    impl_->schema_version=int(version.number(0));
    Statement columns(impl_->database,"SELECT COUNT(*) FROM pragma_table_info('run') WHERE name='execution_backend'");
    columns.row();impl_->execution_metadata=columns.number(0)!=0;
    Statement association(impl_->database,"SELECT COUNT(*) FROM pragma_table_info('run') WHERE name='association_policy'");
    association.row();impl_->association_metadata=association.number(0)!=0;
    impl_->variant=summary().configuration.detector.variant;
}
RunSummary RunStore::summary() const {
    const std::string query=std::string("SELECT created,status,error,source,source_bytes,source_modified,model,model_bytes,model_modified,"
        "confidence,nms,classes,ax,ay,bx,by,direction,deadband,rearm,codec,width,height,duration_us,processed_frames,last_timestamp_us,timestamp_seekable,run_id,") + (impl_->schema_version==1 ? "'nano'" : "model_type") + "," +
        (impl_->schema_version<3 ? "'crossings'" : "run_kind") + " FROM run WHERE id=1";
    Statement row(impl_->database,query.c_str());
    if(!row.row()) throw std::runtime_error("Saved run metadata is missing");
    RunSummary out;
    out.created=row.text(0);out.status=row.text(1);out.error=row.text(2);
    out.configuration.source=path_from(row.text(3));out.source_stamp={std::uint64_t(row.number(4)),row.number(5)};
    out.configuration.detector={path_from(row.text(6)),float(row.real(9)),float(row.real(10)),parse_model(row.text(27))};
    const auto kind=row.text(28);
    if(kind!="appearances" && kind!="crossings")throw std::runtime_error("Invalid saved analysis kind");
    out.configuration.kind=kind=="appearances" ? RunKind::appearances : RunKind::crossings;
    if(impl_->schema_version<4 && model_class_count(out.configuration.detector.variant)>80)
        throw std::runtime_error("Legacy run cannot contain YOLO-World categories");
    if(impl_->schema_version>=4) {
        Statement vocabulary(impl_->database,"SELECT vocabulary_id,vocabulary FROM run WHERE id=1");
        vocabulary.row();
        const auto expected=model_vocabulary(out.configuration.detector.variant);
        if(vocabulary.text(0)!=model_id(out.configuration.detector.variant) || vocabulary.text(1)!=expected)
            throw std::runtime_error("Saved vocabulary does not match the model profile");
    }
    out.model_stamp={std::uint64_t(row.number(7)),row.number(8)};
    out.configuration.tracking.classes.clear();
    std::istringstream classes(row.text(11));std::string token;
    while(std::getline(classes,token,',')) {
        std::size_t end{};const auto id=std::stoi(token,&end);
        if(end!=token.size() || id<0 || !model_has_class(out.configuration.detector.variant,id) || out.configuration.tracking.classes.size()>=std::size_t(model_class_count(out.configuration.detector.variant)))
            throw std::runtime_error("Invalid saved tracking classes");
        out.configuration.tracking.classes.push_back(id);
    }
    out.configuration.tracking.line=CountingLine{{row.real(12),row.real(13)},{row.real(14),row.real(15)},
        static_cast<CrossingDirection>(row.number(16)),row.real(17),row.real(18)};
    if(out.configuration.kind==RunKind::appearances)out.configuration.tracking.line.reset();
    Tracker validate(out.configuration.tracking);
    out.media={row.text(19),int(row.number(20)),int(row.number(21)),row.time(22)};
    out.processed_frames=row.number(23);out.last_timestamp=row.time(24);
    out.timestamp_seekable=row.number(25)!=0;
    out.id=row.text(26);
    if(impl_->execution_metadata) {
        Statement execution(impl_->database,"SELECT requested_backend,gpu_device,execution_backend,execution_runtime,execution_device,execution_fallback FROM run WHERE id=1");
        execution.row();out.configuration.detector.backend=parse_backend(execution.text(0));out.configuration.detector.gpu_device=int(execution.number(1));
        out.execution={execution.text(2),execution.text(3),execution.text(4),execution.text(5)};
    }
    Statement counts(impl_->database,"SELECT COUNT(*),COALESCE(SUM(direction=1),0),COALESCE(SUM(direction=2),0) FROM events");
    if(impl_->association_metadata) {
        Statement association(impl_->database,"SELECT association_policy FROM run WHERE id=1");association.row();
        out.configuration.tracking.association=parse_association(association.text(0));
    }
    counts.row();out.event_count=counts.number(0);out.forward=counts.number(1);out.reverse=counts.number(2);
    if(impl_->schema_version>=3) {
        Statement appearances(impl_->database,"SELECT COUNT(*),COUNT(DISTINCT class_id) FROM appearances");
        appearances.row();out.appearance_count=appearances.number(0);out.class_count=appearances.number(1);
    }
    return out;
}
std::vector<StoredEvent> RunStore::events(std::uint64_t after_id,std::size_t limit) const {
    if(limit==0 || limit>100) throw std::invalid_argument("Event pages contain 1 to 100 rows");
    Statement rows(impl_->database,"SELECT id,track_id,sequence,timestamp_us,class_id,direction,x,y,thumbnail FROM events WHERE id>? ORDER BY id LIMIT ?");
    rows.number(1,integer(after_id));rows.number(2,static_cast<std::int64_t>(limit));
    std::vector<StoredEvent> out;
    while(rows.row()) {
        StoredEvent value;value.event=event_from(rows);
        const auto length=sqlite3_column_bytes(rows.value,8);
        if(length<=0 || length>45000) throw std::runtime_error("Invalid event thumbnail size");
        const auto* data=static_cast<const std::uint8_t*>(sqlite3_column_blob(rows.value,8));
        value.thumbnail.assign(data,data+length);out.push_back(std::move(value));
    }return out;
}
std::vector<StoredAppearance> RunStore::appearances(std::uint64_t after_id,std::size_t limit) const {
    if(limit==0 || limit>100)throw std::invalid_argument("Appearance pages contain 1 to 100 rows");
    if(impl_->schema_version<3)return {};
    Statement rows(impl_->database,"SELECT id,class_id,first_sequence,last_sequence,first_timestamp_us,last_timestamp_us,observations,"
        "first_confidence,peak_confidence,left,top,right,bottom,thumbnail FROM appearances WHERE id>? ORDER BY id LIMIT ?");
    rows.number(1,integer(after_id));rows.number(2,std::int64_t(limit));
    std::vector<StoredAppearance> out;
    while(rows.row()) {
        StoredAppearance value;
        value.id=rows.number(0);value.first_sequence=rows.number(2);value.last_sequence=rows.number(3);
        value.first_timestamp=rows.time(4);value.last_timestamp=rows.time(5);value.observations=rows.number(6);
        value.first_detection={int(rows.number(1)),float(rows.real(7)),float(rows.real(9)),float(rows.real(10)),float(rows.real(11)),float(rows.real(12))};
        value.peak_confidence=float(rows.real(8));
        const auto count=sqlite3_column_bytes(rows.value,13);
        if(count<=0 || count>45000)throw std::runtime_error("Invalid appearance thumbnail size");
        const auto* data=static_cast<const std::uint8_t*>(sqlite3_column_blob(rows.value,13));
        value.thumbnail.assign(data,data+count);out.push_back(std::move(value));
    }
    return out;
}

void RunStore::record_frame(const Frame& frame,std::span<const CrossingEvent> events,std::span<const TrackedObject> objects) {
    impl_->require_writer();
    if(frame.sequence>=std::uint64_t(std::numeric_limits<std::int64_t>::max()))throw std::invalid_argument("Source sequence exceeds SQLite range");
    auto thumb=events.empty() ? std::vector<std::uint8_t>{} : thumbnail(frame);
    impl_->execute("BEGIN IMMEDIATE");
    try {
        for(const auto& event:events) {
            if(event.sequence!=frame.sequence || event.timestamp!=frame.timestamp || event.id==0 || event.track_id==0 ||
                event.class_id<0 || !model_has_class(impl_->variant,event.class_id) || !std::isfinite(event.position.x) || !std::isfinite(event.position.y) ||
                event.position.x<0 || event.position.x>1 || event.position.y<0 || event.position.y>1)
                throw std::invalid_argument("Event does not match its source frame");
            Statement old(impl_->database,"SELECT id,track_id,sequence,timestamp_us,class_id,direction,x,y FROM events WHERE id=?");
            old.number(1,integer(event.id));
            if(old.row()) { if(!same_event(event,event_from(old))) throw std::logic_error("Conflicting saved event ID"); continue; }
            Statement insert(impl_->database,"INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)");
            insert.number(1,integer(event.id));insert.number(2,integer(event.track_id));insert.number(3,integer(event.sequence));
            insert.time(4,event.timestamp);insert.number(5,event.class_id);insert.number(6,static_cast<int>(event.direction));
            insert.real(7,event.position.x);insert.real(8,event.position.y);
            insert.check(sqlite3_bind_blob(insert.value,9,thumb.data(),int(thumb.size()),SQLITE_TRANSIENT));insert.row();
        }
        for(const auto& object:objects) {
            const auto& d=object.detection;
            if(object.id==0 || d.class_id<0 || !model_has_class(impl_->variant,d.class_id) || !std::isfinite(d.confidence) || d.confidence<0 || d.confidence>1 ||
                !std::isfinite(d.left) || !std::isfinite(d.top) || !std::isfinite(d.right) || !std::isfinite(d.bottom) ||
                d.left<0 || d.top<0 || d.right>frame.width || d.bottom>frame.height || d.right<=d.left || d.bottom<=d.top)
                throw std::invalid_argument("Appearance does not match its source frame");
            Statement old(impl_->database,"SELECT class_id,last_sequence,last_timestamp_us FROM appearances WHERE id=?");
            old.number(1,integer(object.id));
            if(old.row()) {
                if(old.number(0)!=d.class_id)throw std::logic_error("Conflicting appearance class");
                if(frame.timestamp && old.time(2) && *frame.timestamp<*old.time(2))throw std::logic_error("Appearance timestamps must not move backwards");
                if(integer(frame.sequence)<old.number(1))throw std::logic_error("Appearance frames must not move backwards");
                if(integer(frame.sequence)==old.number(1)) {
                    if(old.time(2)!=frame.timestamp)throw std::logic_error("Conflicting appearance timestamp");
                    continue;
                }
                Statement update(impl_->database,"UPDATE appearances SET last_sequence=?,last_timestamp_us=?,observations=observations+1,peak_confidence=MAX(peak_confidence,?) WHERE id=?");
                update.number(1,integer(frame.sequence));update.time(2,frame.timestamp);update.real(3,d.confidence);update.number(4,integer(object.id));update.row();
            } else {
                if(thumb.empty())thumb=thumbnail(frame);
                Statement insert(impl_->database,"INSERT INTO appearances VALUES(?,?,?,?,?,?,1,?,?,?,?,?,?,?)");
                insert.number(1,integer(object.id));insert.number(2,d.class_id);insert.number(3,integer(frame.sequence));insert.number(4,integer(frame.sequence));
                insert.time(5,frame.timestamp);insert.time(6,frame.timestamp);insert.real(7,d.confidence);insert.real(8,d.confidence);
                insert.real(9,d.left);insert.real(10,d.top);insert.real(11,d.right);insert.real(12,d.bottom);
                insert.check(sqlite3_bind_blob(insert.value,13,thumb.data(),int(thumb.size()),SQLITE_TRANSIENT));insert.row();
            }
        }
        Statement update(impl_->database,"UPDATE run SET timestamp_seekable=timestamp_seekable AND (? IS NOT NULL) AND "
            "(processed_frames=0 OR ?>last_timestamp_us),processed_frames=?,last_timestamp_us=? WHERE id=1 AND processed_frames<?");
        update.time(1,frame.timestamp);update.time(2,frame.timestamp);update.number(3,integer(frame.sequence)+1);
        update.time(4,frame.timestamp);update.number(5,integer(frame.sequence)+1);update.row();
        impl_->execute("COMMIT");
    } catch(...) { sqlite3_exec(impl_->database,"ROLLBACK",nullptr,nullptr,nullptr);throw; }
}
void RunStore::finish(std::string_view status,std::string_view error) {
    impl_->require_writer();
    if(status!="completed" && status!="cancelled" && status!="failed") throw std::invalid_argument("Invalid final run status");
    Statement update(impl_->database,"UPDATE run SET status=?,error=? WHERE id=1");update.text(1,status);update.text(2,error);update.row();
}
void RunStore::record_execution(const ExecutionInfo& execution) {
    impl_->require_writer();
    if(impl_->last_execution==execution)return;
    Statement update(impl_->database,"UPDATE run SET execution_backend=?,execution_runtime=?,execution_device=?,execution_fallback=? WHERE id=1");
    update.text(1,execution.provider);update.text(2,execution.runtime);update.text(3,execution.device);update.text(4,execution.fallback);update.row();
    impl_->last_execution=execution;
}
bool RunStore::source_available() const {
    const auto info=summary();try { return file_stamp(info.configuration.source)==info.source_stamp; }catch(...) {return false;}
}
void RunStore::export_csv(const std::filesystem::path& output) const {
    const auto info=summary();
    auto* file=exclusive_file(output);
    try {
        const auto write=[&](const std::string& value) {
            if(std::fwrite(value.data(),1,value.size(),file)!=value.size())throw std::runtime_error("Could not write event CSV");
        };
        write("run_id,source,run_status,event_id,sequence,timestamp_us,track_id,class_id,class,direction,x,y\n");
        std::uint64_t after{};
        for(;;) {
            const auto page=events(after);if(page.empty())break;
            for(const auto& value:page) {
                const auto& e=value.event;std::ostringstream line;line.precision(17);
                line<<quote(info.id)<<','<<quote(utf8(info.configuration.source))<<','<<quote(info.status)<<','<<e.id<<','<<e.sequence<<',';
                if(e.timestamp)line<<e.timestamp->count();
                line<<','<<e.track_id<<','<<e.class_id<<','<<quote(class_name(e.class_id))<<','<<quote(direction_name(e.direction))
                    <<','<<e.position.x<<','<<e.position.y<<'\n';write(line.str());after=e.id;
            }
        }
        const auto result=std::fclose(file);file=nullptr;if(result!=0)throw std::runtime_error("Could not finish event CSV");
    }catch(...) {
        if(file)std::fclose(file);
        std::error_code ignored;std::filesystem::remove(output,ignored);throw;
    }
}
void RunStore::export_appearances_csv(const std::filesystem::path& output) const {
    const auto info=summary();
    auto* file=exclusive_file(output);
    const auto formatted=[](std::optional<std::chrono::microseconds> time) {
        if(!time)return std::string{};
        const auto ms=std::max<std::int64_t>(0,time->count()/1000);
        std::ostringstream value;
        value<<std::setfill('0')<<std::setw(2)<<ms/3600000<<':'<<std::setw(2)<<(ms/60000)%60<<':'
             <<std::setw(2)<<(ms/1000)%60<<'.'<<std::setw(3)<<ms%1000;
        return value.str();
    };
    try {
        const auto write=[&](const std::string& value) {
            if(std::fwrite(value.data(),1,value.size(),file)!=value.size())throw std::runtime_error("Could not write appearance CSV");
        };
        write("\xef\xbb\xbfObject,Appearance ID,First seen,Last seen,Span seconds,Observations,Peak confidence percent,First frame,Last frame,First timestamp us,Last timestamp us,Video,Analysis status,Model,Run ID,Execution provider,Runtime,Device,CPU fallback\r\n");
        std::uint64_t after{};
        for(;;) {
            const auto page=appearances(after);if(page.empty())break;
            for(const auto& item:page) {
                std::ostringstream line;line.imbue(std::locale::classic());line<<std::fixed<<std::setprecision(3);
                line<<quote(class_name(item.first_detection.class_id))<<','<<item.id<<','<<formatted(item.first_timestamp)<<','<<formatted(item.last_timestamp)<<',';
                if(item.first_timestamp && item.last_timestamp)line<<std::chrono::duration<double>(*item.last_timestamp-*item.first_timestamp).count();
                line<<','<<item.observations<<','<<std::setprecision(2)<<item.peak_confidence*100<<','<<item.first_sequence<<','<<item.last_sequence<<',';
                if(item.first_timestamp)line<<item.first_timestamp->count();line<<',';
                if(item.last_timestamp)line<<item.last_timestamp->count();
                line<<','<<quote(utf8(info.configuration.source.filename()))<<','<<quote(info.status)<<','<<quote(model_name(info.configuration.detector.variant))<<','<<quote(info.id)
                    <<','<<quote(info.execution.provider)<<','<<quote(info.execution.runtime)<<','<<quote(info.execution.device)<<','<<quote(info.execution.fallback)<<"\r\n";
                write(line.str());after=item.id;
            }
        }
        const auto result=std::fclose(file);file=nullptr;if(result!=0)throw std::runtime_error("Could not finish appearance CSV");
    } catch(...) {
        if(file)std::fclose(file);
        std::error_code ignored;std::filesystem::remove(output,ignored);throw;
    }
}

}
