#include "assignment.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace frametrail::association {
std::vector<std::optional<std::size_t>> assign(std::size_t rows,std::size_t tracks,std::span<const Edge> edges) {
    if(rows>256 || tracks>512)throw std::invalid_argument("Association exceeds bounded tracker dimensions");
    std::vector<std::optional<std::size_t>> result(rows);
    double maximum{};
    for(const auto& edge:edges) {
        if(edge.observation>=rows || edge.track>=tracks || !std::isfinite(edge.cost) || edge.cost<0 || edge.cost>16)
            throw std::invalid_argument("Invalid association edge");
        maximum=std::max(maximum,edge.cost);
    }
    if(edges.empty())return result;
    // Losing one valid match costs more than every possible real-edge cost combined.
    const double unmatched=(rows+1)*(maximum+1),forbidden=(rows+1)*unmatched;
    const auto columns=tracks+rows;
    std::vector<double> cost(rows*columns,unmatched);
    for(std::size_t row=0;row<rows;++row)std::fill_n(cost.begin()+row*columns,tracks,forbidden);
    for(const auto& edge:edges)cost[edge.observation*columns+edge.track]=std::min(cost[edge.observation*columns+edge.track],edge.cost);
    // Rectangular Hungarian shortest augmenting paths. Potentials keep reduced
    // costs nonnegative; ascending columns give repeatable exact-tie behaviour.
    std::vector<double> u(rows+1),v(columns+1);
    std::vector<std::size_t> owner(columns+1),way(columns+1);
    for(std::size_t row=1;row<=rows;++row) {
        owner[0]=row;std::size_t column{};
        std::vector<double> minimum(columns+1,std::numeric_limits<double>::infinity());
        std::vector<bool> visited(columns+1);
        do {
            visited[column]=true;const auto active=owner[column];
            double delta=std::numeric_limits<double>::infinity();std::size_t next{};
            for(std::size_t j=1;j<=columns;++j)if(!visited[j]) {
                const auto reduced=cost[(active-1)*columns+j-1]-u[active]-v[j];
                if(reduced<minimum[j]){minimum[j]=reduced;way[j]=column;}
                if(minimum[j]<delta){delta=minimum[j];next=j;}
            }
            for(std::size_t j=0;j<=columns;++j) {
                if(visited[j]){u[owner[j]]+=delta;v[j]-=delta;}else minimum[j]-=delta;
            }
            column=next;
        }while(owner[column]);
        do {const auto previous=way[column];owner[column]=owner[previous];column=previous;}while(column);
    }
    for(std::size_t column=1;column<=tracks;++column)if(owner[column] && cost[(owner[column]-1)*columns+column-1]<unmatched)
        result[owner[column]-1]=column-1;
    return result;
}
}
