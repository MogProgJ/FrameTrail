#include "frametrail/tracker.hpp"
#include "assignment.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <tuple>

namespace frametrail {
namespace {
Point anchor(const Detection& d, int width, int height) {
    return {(d.left + d.right) / (2.0 * width), d.bottom / double(height)};
}
double cross(Point a, Point b) { return a.x * b.y - a.y * b.x; }
Point subtract(Point a, Point b) { return {a.x - b.x, a.y - b.y}; }
double length(Point p) { return std::hypot(p.x, p.y); }
double signed_distance(Point p, const CountingLine& line) {
    const auto axis = subtract(line.b, line.a);
    return cross(axis, subtract(p, line.a)) / length(axis);
}
std::optional<Point> intersection(Point from, Point to, const CountingLine& line) {
    const auto movement = subtract(to, from), axis = subtract(line.b, line.a);
    const auto denominator = cross(movement, axis);
    if (std::abs(denominator) < 1e-12) return {};
    const auto offset = subtract(line.a, from);
    const double t = cross(offset, axis) / denominator, u = cross(offset, movement) / denominator;
    if (t < 0 || t > 1 || u < 0 || u > 1) return {};
    return Point{from.x + t * movement.x, from.y + t * movement.y};
}
double iou(const Detection& a, const Detection& b) {
    const double area = std::max(0.0f, std::min(a.right,b.right)-std::max(a.left,b.left)) *
        std::max(0.0f, std::min(a.bottom,b.bottom)-std::max(a.top,b.top));
    const double total = (a.right-a.left)*(a.bottom-a.top)+(b.right-b.left)*(b.bottom-b.top)-area;
    return total > 0 ? area / total : 0;
}
bool finite(Point p) { return std::isfinite(p.x) && std::isfinite(p.y); }
bool in_frame(Point p) { return finite(p) && p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1; }
bool valid_direction(CrossingDirection d) {
    return d == CrossingDirection::both || d == CrossingDirection::negative_to_positive ||
        d == CrossingDirection::positive_to_negative;
}
}

std::string_view direction_name(CrossingDirection direction) {
    switch (direction) {
    case CrossingDirection::negative_to_positive: return "negative_to_positive";
    case CrossingDirection::positive_to_negative: return "positive_to_negative";
    default: return "both";
    }
}
std::string_view association_name(AssociationPolicy policy) {
    if(policy==AssociationPolicy::greedy)return "greedy";
    if(policy==AssociationPolicy::repair)return "repair";
    throw std::invalid_argument("Invalid association policy");
}
AssociationPolicy parse_association(std::string_view name) {
    if(name=="greedy")return AssociationPolicy::greedy;
    if(name=="repair")return AssociationPolicy::repair;
    throw std::invalid_argument("Association must be greedy or repair");
}

struct Tracker::Impl {
    struct Track {
        std::uint64_t id{}, sequence{};
        std::optional<std::chrono::microseconds> timestamp;
        Detection box;
        Point velocity{}; // Normalized displacement per sequence step.
        Point time_velocity{}; // Normalized displacement per source second.
        unsigned hits{1};
        std::vector<Point> trail;
        int side{};
        Point stable_anchor{};
        bool armed{};
    };
    TrackingOptions options;
    std::vector<Track> tracks;
    std::optional<std::uint64_t> last_sequence;
    std::optional<std::chrono::microseconds> last_timestamp;
    int width{}, height{};
    std::uint64_t next_track{1}, next_event{1}, forward{}, reverse{};

    static bool gap_exceeds(const Track& track, std::uint64_t sequence,
        std::optional<std::chrono::microseconds> timestamp, std::int64_t us, std::uint64_t frames) {
        if (timestamp && track.timestamp) return *timestamp - *track.timestamp > std::chrono::microseconds(us);
        return sequence - track.sequence > frames;
    }
    void crossing(Track& track, Point p, TrackingResult& result) {
        if (!options.line) return;
        const auto& line = *options.line;
        const auto distance = signed_distance(p,line);
        const int side = distance > line.deadband ? 1 : distance < -line.deadband ? -1 : 0;
        if (side == 0) return; // Retain last stable side through the deadband.
        if (track.side != 0 && side != track.side) {
            const auto point = intersection(track.stable_anchor,p,line);
            const auto direction = side > 0 ? CrossingDirection::negative_to_positive : CrossingDirection::positive_to_negative;
            if (track.armed && track.hits >= 3 && point &&
                (line.direction == CrossingDirection::both || line.direction == direction)) {
                result.events.push_back({next_event++,track.id,track.sequence,track.timestamp,
                    track.box.class_id,direction,*point});
                if (side > 0) ++forward; else ++reverse;
            }
            // Even a filtered crossing consumes the arm. Re-arm on a later observation.
            track.armed = false;
        } else if (std::abs(distance) >= line.rearm_distance) {
            track.armed = true;
        }
        track.side = side;
        track.stable_anchor = p;
    }
};

Tracker::Tracker(TrackingOptions options) : impl_(std::make_unique<Impl>()) {
    association_name(options.association);
    if (options.classes.empty()) throw std::invalid_argument("Tracking needs at least one class");
    for (int id : options.classes) if (id < 0 || id >= 80) throw std::invalid_argument("Tracking class must be a COCO ID in [0,79]");
    if (options.line) {
        const auto& line = *options.line;
        if (!in_frame(line.a) || !in_frame(line.b) || length(subtract(line.b,line.a)) < 0.05 ||
            !std::isfinite(line.deadband) || !std::isfinite(line.rearm_distance) ||
            line.deadband <= 0 || line.rearm_distance <= line.deadband || !valid_direction(line.direction))
            throw std::invalid_argument("Counting line needs distinct normalized endpoints and valid hysteresis");
    }
    impl_->options = std::move(options);
}
Tracker::~Tracker() = default;
void Tracker::reset_continuity(){impl_->tracks.clear();}

TrackingResult Tracker::update(std::span<const Detection> detections, std::uint64_t sequence,
    std::optional<std::chrono::microseconds> timestamp, int width, int height) {
    const auto start = std::chrono::steady_clock::now();
    auto& s = *impl_;
    if (width <= 0 || height <= 0) throw std::invalid_argument("Invalid tracking dimensions");
    if (s.last_sequence && sequence <= *s.last_sequence) throw std::invalid_argument("Tracking needs strictly increasing frame sequences");
    if (timestamp && s.last_timestamp && *timestamp < *s.last_timestamp) throw std::invalid_argument("Tracking timestamps must not move backwards");
    std::vector<Detection> selected;
    for (const auto& d : detections) {
        if (!std::isfinite(d.left) || !std::isfinite(d.top) || !std::isfinite(d.right) || !std::isfinite(d.bottom) ||
            !std::isfinite(d.confidence) || d.left < 0 || d.top < 0 || d.right > width || d.bottom > height ||
            d.right <= d.left || d.bottom <= d.top) throw std::invalid_argument("Invalid tracking box");
        if (std::ranges::find(s.options.classes,d.class_id) != s.options.classes.end()) selected.push_back(d);
    }
    if (selected.size() > 256) throw std::runtime_error("Tracking baseline supports at most 256 selected detections per frame");
    if (s.width != width || s.height != height) s.tracks.clear(); // Do not bridge coordinate changes.
    std::erase_if(s.tracks,[&](const auto& t) { return Impl::gap_exceeds(t,sequence,timestamp,750000,15); });

    std::vector<association::Edge> candidates;
    for (std::size_t i = 0; i < s.tracks.size(); ++i) {
        const auto& track = s.tracks[i];
        auto predicted = track.box;
        const auto steps = double(sequence - track.sequence);
        const bool timed = timestamp && track.timestamp && *timestamp > *track.timestamp;
        const auto seconds = timed ? std::chrono::duration<double>(*timestamp-*track.timestamp).count() : 0;
        const auto dx = float((timed ? track.time_velocity.x*seconds : track.velocity.x*steps)*width);
        const auto dy = float((timed ? track.time_velocity.y*seconds : track.velocity.y*steps)*height);
        predicted.left += dx; predicted.right += dx; predicted.top += dy; predicted.bottom += dy;
        for (std::size_t j = 0; j < selected.size(); ++j) {
            const auto& d = selected[j];
            if (d.class_id != track.box.class_id) continue;
            const double predicted_distance = length(subtract(anchor(predicted,width,height),anchor(d,width,height)));
            // A small fallback penalty keeps motion prediction preferred while
            // allowing an abrupt stop/reversal without discarding the identity.
            const double observed_distance = length(subtract(anchor(track.box,width,height),anchor(d,width,height)));
            const double distance = std::min(predicted_distance,observed_distance);
            const double scored_distance = std::min(predicted_distance,observed_distance+0.02);
            const double scale = std::max({(d.right-d.left)/double(width),(d.bottom-d.top)/double(height),0.02});
            const double overlap = std::max(iou(predicted,d),iou(track.box,d));
            // Reject distant pairs, even when a large box overlaps by accident.
            if (distance <= 0.15 && (overlap >= 0.05 || distance <= scale))
                candidates.push_back({j,i,scored_distance / scale + (1-overlap)*0.25});
        }
    }
    // Preserve the established baseline when it already achieves maximum possible
    // coverage. Global reassignment is a repair for avoidable fragmentation, not
    // a reason to reshuffle every ambiguous same-class crowd on each frame.
    std::ranges::sort(candidates,[](const auto& a,const auto& b){return std::tie(a.cost,a.track,a.observation)<std::tie(b.cost,b.track,b.observation);});
    std::vector<std::optional<std::size_t>> matches(selected.size());std::vector<bool> used(s.tracks.size());std::size_t assigned{};
    for(const auto& edge:candidates)if(!matches[edge.observation] && !used[edge.track]) {
        matches[edge.observation]=edge.track;used[edge.track]=true;++assigned;
    }
    if(s.options.association==AssociationPolicy::repair && assigned<std::min(selected.size(),s.tracks.size())) {
        auto repaired=association::assign(selected.size(),s.tracks.size(),candidates);
        const auto count=std::ranges::count_if(repaired,[](const auto& value){return value.has_value();});
        if(std::size_t(count)>assigned)matches=std::move(repaired);
    }
    TrackingResult result;
    for (std::size_t j = 0; j < selected.size(); ++j) {
        const auto p = anchor(selected[j],width,height);
        if (!matches[j]) {
            // Bound active state; fail explicitly rather than discard identities silently.
            if (s.tracks.size() >= 512) throw std::runtime_error("Tracking baseline exceeded 512 active tracks");
            Impl::Track track;
            track.id = s.next_track++; track.box = selected[j]; track.sequence = sequence; track.timestamp = timestamp;
            s.tracks.push_back(std::move(track));
            matches[j] = s.tracks.size()-1;
        } else {
            auto& track = s.tracks[*matches[j]];
            const bool gap = Impl::gap_exceeds(track,sequence,timestamp,250000,3);
            const auto previous = anchor(track.box,width,height);
            const auto steps = double(sequence-track.sequence);
            track.velocity = {(p.x-previous.x)/steps,(p.y-previous.y)/steps};
            if (timestamp && track.timestamp && *timestamp > *track.timestamp) {
                const auto seconds = std::chrono::duration<double>(*timestamp-*track.timestamp).count();
                track.time_velocity = {(p.x-previous.x)/seconds,(p.y-previous.y)/seconds};
            } else track.time_velocity = {};
            if (gap) { track.side = 0; track.armed = false; track.trail.clear(); track.hits=0; }
            track.box = selected[j]; track.sequence = sequence; track.timestamp = timestamp; ++track.hits;
        }
        auto& track = s.tracks[*matches[j]];
        track.trail.push_back(p);
        if (track.trail.size() > 20) track.trail.erase(track.trail.begin());
        s.crossing(track,p,result);
        result.objects.push_back({track.id,track.box,track.hits >= 3,track.trail});
    }
    s.width = width; s.height = height; s.last_sequence = sequence; s.last_timestamp = timestamp;
    result.negative_to_positive = s.forward; result.positive_to_negative = s.reverse;
    result.elapsed_ms = std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
    return result;
}
} // namespace frametrail
