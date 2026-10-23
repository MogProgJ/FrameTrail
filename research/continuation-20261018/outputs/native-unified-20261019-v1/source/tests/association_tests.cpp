#include "assignment.hpp"
#include <cmath>
#include <chrono>
#include <functional>
#include <iostream>
#include <random>
#include <set>
#include <stdexcept>

using namespace frametrail::association;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
int main() {
    try {
        std::mt19937 random(711);
        for(unsigned trial=0;trial<400;++trial) {
            const std::size_t rows=1+random()%4,tracks=1+random()%4;
            std::vector<Edge> edges;
            for(std::size_t row=0;row<rows;++row)for(std::size_t track=0;track<tracks;++track)
                if(random()%3)edges.push_back({row,track,double(random()%100)/10});
            unsigned best_count{};double best_cost=1e9;
            std::function<void(std::size_t,unsigned,double,std::set<std::size_t>)> brute;
            brute=[&](std::size_t row,unsigned count,double cost,std::set<std::size_t> used) {
                if(row==rows){if(count>best_count || (count==best_count && cost<best_cost)){best_count=count;best_cost=cost;}return;}
                brute(row+1,count,cost,used);
                for(const auto& edge:edges)if(edge.observation==row && !used.contains(edge.track)) {
                    auto next=used;next.insert(edge.track);brute(row+1,count+1,cost+edge.cost,std::move(next));
                }
            };
            brute(0,0,0,{});
            const auto assignment=assign(rows,tracks,edges);std::set<std::size_t> used;double cost{};
            for(std::size_t row=0;row<rows;++row)if(assignment[row]) {
                require(used.insert(*assignment[row]).second,"Association reused a track");bool found{};
                for(const auto& edge:edges)if(edge.observation==row && edge.track==*assignment[row]){cost+=edge.cost;found=true;break;}
                require(found,"Association selected a forbidden edge");
            }
            require(used.size()==best_count && std::abs(cost-best_cost)<1e-7,"Global matching disagreed with exhaustive optimum");
            require(assignment==assign(rows,tracks,edges),"Tie resolution was not repeatable");
        }
        std::vector<Edge> dense;for(std::size_t row=0;row<256;++row)for(std::size_t track=0;track<512;++track)dense.push_back({row,track,1});
        const auto begin=std::chrono::steady_clock::now();const auto result=assign(256,512,dense);
        std::set<std::size_t> unique;for(const auto& item:result){require(item.has_value(),"Dense bounded assignment dropped a match");unique.insert(*item);}
        require(unique.size()==256,"Dense bounded assignment reused a track");
        require(assign(0,0,{}).empty(),"Empty association failed");
        bool rejected{};try{assign(257,0,{});}catch(const std::invalid_argument&){rejected=true;}require(rejected,"Association bounds were ignored");
        std::cout<<"400 exhaustive optimum comparisons and dense 256x512 assignment passed; dense ms="
            <<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count()<<'\n';return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
