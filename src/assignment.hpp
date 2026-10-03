#pragma once
#include <cstddef>
#include <optional>
#include <span>
#include <vector>

namespace frametrail::association {
struct Edge {std::size_t observation{},track{};double cost{};};
// Maximum cardinality first, then minimum total cost among permitted edges.
// Rows are observations, real columns are tracks; private dummy columns mean unmatched.
std::vector<std::optional<std::size_t>> assign(std::size_t observations,std::size_t tracks,std::span<const Edge> edges);
}
