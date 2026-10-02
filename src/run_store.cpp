#include "frametrail/run_store.hpp"
#include <sqlite3.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <limits>
#include <sstream>
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
    if(!config.tracking.line) throw std::invalid_argument("Saved crossing analysis requires a counting line");
    const auto source=std::filesystem::absolute(config.source), model=std::filesystem::absolute(config.detector.model);
    const auto source_stamp=file_stamp(source),model_stamp=file_stamp(model);
    // Validate native model/tracker settings before creating any output.
    Tracker validation(config.tracking);
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
    auto impl=std::make_unique<Impl>(database,true);
    impl->execute("PRAGMA application_id=1179931212; PRAGMA user_version=1; PRAGMA trusted_schema=OFF; PRAGMA foreign_keys=ON;");
    impl->execute("BEGIN IMMEDIATE");
    impl->execute("CREATE TABLE run(id INTEGER PRIMARY KEY CHECK(id=1),created TEXT NOT NULL,status TEXT NOT NULL,"
        "error TEXT NOT NULL DEFAULT '',source TEXT NOT NULL,source_bytes INTEGER NOT NULL,source_modified INTEGER NOT NULL,"
        "model TEXT NOT NULL,model_bytes INTEGER NOT NULL,model_modified INTEGER NOT NULL,confidence REAL NOT NULL,nms REAL NOT NULL,"
        "classes TEXT NOT NULL,ax REAL NOT NULL,ay REAL NOT NULL,bx REAL NOT NULL,by REAL NOT NULL,direction INTEGER NOT NULL,"
        "deadband REAL NOT NULL,rearm REAL NOT NULL,codec TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,"
        "duration_us INTEGER,processed_frames INTEGER NOT NULL DEFAULT 0,last_timestamp_us INTEGER,timestamp_seekable INTEGER NOT NULL DEFAULT 1,"
        "run_id TEXT NOT NULL DEFAULT(lower(hex(randomblob(16)))),"
        "engine TEXT NOT NULL DEFAULT 'FrameTrail 0.6 / YOLOX-Nano 0.1.1rc0 / ORT 1.30.0 CPU / tracker-v1');"
        "CREATE TABLE events(id INTEGER PRIMARY KEY CHECK(id>0),track_id INTEGER NOT NULL,sequence INTEGER NOT NULL,"
        "timestamp_us INTEGER,class_id INTEGER NOT NULL,direction INTEGER NOT NULL CHECK(direction IN(1,2)),"
        "x REAL NOT NULL,y REAL NOT NULL,thumbnail BLOB NOT NULL);" );
    Statement insert(impl->database,"INSERT INTO run(id,created,status,source,source_bytes,source_modified,model,model_bytes,model_modified,"
        "confidence,nms,classes,ax,ay,bx,by,direction,deadband,rearm,codec,width,height,duration_us)"
        " VALUES(1,strftime('%Y-%m-%dT%H:%M:%fZ','now'),'running',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
    insert.text(1,utf8(source)); insert.number(2,integer(source_stamp.bytes)); insert.number(3,source_stamp.modified);
    insert.text(4,utf8(model)); insert.number(5,integer(model_stamp.bytes)); insert.number(6,model_stamp.modified);
    insert.real(7,config.detector.confidence);insert.real(8,config.detector.nms_iou);
    std::string classes;for(auto id:config.tracking.classes) { if(!classes.empty())classes+=',';classes+=std::to_string(id); }
    insert.text(9,classes); const auto& line=*config.tracking.line;
    insert.real(10,line.a.x);insert.real(11,line.a.y);insert.real(12,line.b.x);insert.real(13,line.b.y);
    insert.number(14,static_cast<int>(line.direction));insert.real(15,line.deadband);insert.real(16,line.rearm_distance);
    insert.text(17,media.codec);insert.number(18,media.width);insert.number(19,media.height);insert.time(20,media.duration);
    insert.row();impl->execute("COMMIT");guard.ready=true;return RunStore(std::move(impl));
}
RunStore::RunStore(const std::filesystem::path& database):impl_(std::make_unique<Impl>(database,false)) {
    impl_->execute("PRAGMA trusted_schema=OFF");
    Statement app(impl_->database,"PRAGMA application_id"),version(impl_->database,"PRAGMA user_version");
    if(!app.row() || app.number(0)!=application_id || !version.row() || version.number(0)!=1)
        throw std::runtime_error("This is not a supported FrameTrail run (schema version 1)");
    summary();
}
RunSummary RunStore::summary() const {
    Statement row(impl_->database,"SELECT created,status,error,source,source_bytes,source_modified,model,model_bytes,model_modified,"
        "confidence,nms,classes,ax,ay,bx,by,direction,deadband,rearm,codec,width,height,duration_us,processed_frames,last_timestamp_us,timestamp_seekable,run_id FROM run WHERE id=1");
    if(!row.row()) throw std::runtime_error("Saved run metadata is missing");
    RunSummary out;
    out.created=row.text(0);out.status=row.text(1);out.error=row.text(2);
    out.configuration.source=path_from(row.text(3));out.source_stamp={std::uint64_t(row.number(4)),row.number(5)};
    out.configuration.detector={path_from(row.text(6)),float(row.real(9)),float(row.real(10))};
    out.model_stamp={std::uint64_t(row.number(7)),row.number(8)};
    out.configuration.tracking.classes.clear();
    std::istringstream classes(row.text(11));std::string token;
    while(std::getline(classes,token,',')) {
        std::size_t end{};const auto id=std::stoi(token,&end);
        if(end!=token.size() || id<0 || id>=80 || out.configuration.tracking.classes.size()>=80)
            throw std::runtime_error("Invalid saved tracking classes");
        out.configuration.tracking.classes.push_back(id);
    }
    out.configuration.tracking.line=CountingLine{{row.real(12),row.real(13)},{row.real(14),row.real(15)},
        static_cast<CrossingDirection>(row.number(16)),row.real(17),row.real(18)};
    Tracker validate(out.configuration.tracking);
    out.media={row.text(19),int(row.number(20)),int(row.number(21)),row.time(22)};
    out.processed_frames=row.number(23);out.last_timestamp=row.time(24);
    out.timestamp_seekable=row.number(25)!=0;
    out.id=row.text(26);
    Statement counts(impl_->database,"SELECT COUNT(*),COALESCE(SUM(direction=1),0),COALESCE(SUM(direction=2),0) FROM events");
    counts.row();out.event_count=counts.number(0);out.forward=counts.number(1);out.reverse=counts.number(2);
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
void RunStore::record_frame(const Frame& frame,std::span<const CrossingEvent> events) {
    impl_->require_writer();
    if(frame.sequence>=std::uint64_t(std::numeric_limits<std::int64_t>::max()))throw std::invalid_argument("Source sequence exceeds SQLite range");
    const auto thumb=events.empty() ? std::vector<std::uint8_t>{} : thumbnail(frame);
    impl_->execute("BEGIN IMMEDIATE");
    try {
        for(const auto& event:events) {
            if(event.sequence!=frame.sequence || event.timestamp!=frame.timestamp || event.id==0 || event.track_id==0 ||
                event.class_id<0 || event.class_id>=80 || !std::isfinite(event.position.x) || !std::isfinite(event.position.y) ||
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
}
