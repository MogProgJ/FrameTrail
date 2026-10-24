#pragma once
#include <QCoreApplication>
#include <QDateTime>
#include <QFileInfo>
#include <QSettings>
#include <QStringList>
#include <QVector>

// Recently opened media and analyses for the Home page, kept in the per-user settings.
// Only the app sets an organisation name (main.cpp), so test programs never record anything.
struct RecentFile { QString path; QDateTime opened; };

inline QVector<RecentFile> recent_files() {
    QVector<RecentFile> out;
    if(QCoreApplication::organizationName().isEmpty())return out;
    for(const auto& entry:QSettings().value(QStringLiteral("recent/files")).toStringList()) {
        const auto split=entry.indexOf(QLatin1Char('|'));
        if(split>0)out.push_back({entry.mid(split+1),QDateTime::fromString(entry.left(split),Qt::ISODate)});
    }
    return out;
}
inline void remember_file(const QString& path) {
    if(QCoreApplication::organizationName().isEmpty() || path.isEmpty())return;
    const auto absolute=QFileInfo(path).absoluteFilePath();
    QStringList entries{QDateTime::currentDateTime().toString(Qt::ISODate)+QLatin1Char('|')+absolute};
    for(const auto& file:recent_files())if(file.path.compare(absolute,Qt::CaseInsensitive)!=0 && entries.size()<12)
        entries<<file.opened.toString(Qt::ISODate)+QLatin1Char('|')+file.path;
    QSettings().setValue(QStringLiteral("recent/files"),entries);
}
inline void clear_recent_files() {
    if(!QCoreApplication::organizationName().isEmpty())QSettings().remove(QStringLiteral("recent/files"));
}
