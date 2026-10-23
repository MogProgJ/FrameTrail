#pragma once
#include <QString>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <optional>

// Display estimates only; never used for scheduling, detection or saved results.
struct ProcessingFeedback { QString text; std::optional<int> permille; };
inline QString work_duration(double seconds) {
    const auto value=static_cast<qint64>(std::clamp(seconds,0.,31536000.));
    if(value<60)return QStringLiteral("%1s").arg(value);
    if(value<3600)return QStringLiteral("%1m %2s").arg(value/60).arg(value%60);
    return QStringLiteral("%1h %2m").arg(value/3600).arg(value%3600/60);
}
inline ProcessingFeedback processing_feedback(std::uint64_t frames,double elapsed,
    std::optional<std::chrono::microseconds> first,std::optional<std::chrono::microseconds> timestamp,
    std::optional<std::chrono::microseconds> duration) {
    ProcessingFeedback out;
    out.text=QStringLiteral("%1 frames · %2 elapsed").arg(frames).arg(work_duration(elapsed));
    if(frames && elapsed>=1)out.text+=QStringLiteral(" · %1 fps").arg(double(frames)/elapsed,0,'f',1);
    // Source timestamps may begin above/below zero. Missing or non-advancing
    // timestamps do not support a duration-based estimate.
    if(first && timestamp && duration && duration->count()>0 && *timestamp>=*first) {
        const double fraction=double((*timestamp-*first).count())/double(duration->count());
        out.permille=int(std::clamp(fraction*1000.,0.,999.));
        if(frames>=8 && elapsed>=1 && fraction>0 && fraction<1) {
            const double remaining=elapsed*(1/fraction-1);
            if(std::isfinite(remaining) && remaining<=31536000.) {
                out.text+=QStringLiteral(" · about %1 left").arg(work_duration(std::ceil(remaining)));return out;
            }
        }
    }
    out.text+=QStringLiteral(" · estimating time left");return out;
}
