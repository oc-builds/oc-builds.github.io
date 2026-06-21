// ============================================================================
// File        : PrereqGraph.cpp
// Author      : Sanjay Chauhan
// Date        : 2026-05-31
// Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
//               PrereqGraph implementation. Adjacency list storage and three
//               color DFS for cycle detection.
// ============================================================================

#include "PrereqGraph.h"

#include <algorithm>

// O(1) amortized.
void PrereqGraph::AddNode(const std::string& id) {
  // operator[] inserts a default-constructed empty vector if absent, which
  // is the desired "registered but no outgoing edges yet" state.
  adj_[id];
}

// O(1) amortized.
void PrereqGraph::AddEdge(const std::string& from, const std::string& to) {
  adj_[from].push_back(to);
}

// O(V + E). Walks every adjacency list once. A target is reported as
// missing when it is not in known_set. Returned IDs are de-duplicated and
// sorted so the warning output is deterministic regardless of hash-map
// iteration order.
std::vector<std::string> PrereqGraph::ValidateMissing(
    const std::vector<std::string>& known_ids) const {
  std::unordered_set<std::string> known_set(known_ids.begin(), known_ids.end());
  std::unordered_set<std::string> missing_set;

  for (const auto& [from, targets] : adj_) {
    (void)from;  // unused: we only care about the edge targets
    for (const auto& to : targets) {
      if (known_set.find(to) == known_set.end()) {
        missing_set.insert(to);
      }
    }
  }

  std::vector<std::string> missing(missing_set.begin(), missing_set.end());
  std::sort(missing.begin(), missing.end());
  return missing;
}

// O(deg(u) + descendants). Standard iterative-friendly recursive DFS that
// records the active path in stack so the cycle can be reconstructed when
// a GRAY successor is encountered.
bool PrereqGraph::DfsVisit(const std::string& u,
                           std::unordered_map<std::string, Color>& color,
                           std::vector<std::string>& stack,
                           std::vector<std::string>& cycle_out) const {
  color[u] = Color::kGray;
  stack.push_back(u);

  const auto it = adj_.find(u);
  if (it != adj_.end()) {
    for (const auto& v : it->second) {
      // Skip edges to nodes that were never registered. Those are handled by
      // ValidateMissing; treating them as graph members here would risk a
      // false positive for the cycle check.
      if (adj_.find(v) == adj_.end()) {
        continue;
      }

      const Color cv = color[v];
      if (cv == Color::kGray) {
        // Back edge to an ancestor on the current path: cycle found.
        // Walk the stack from v's first occurrence to the end to capture
        // the cycle in the order the courses depend on each other.
        const auto start =
            std::find(stack.begin(), stack.end(), v);
        cycle_out.assign(start, stack.end());
        cycle_out.push_back(v);  // close the loop visually
        return true;
      }
      if (cv == Color::kWhite) {
        if (DfsVisit(v, color, stack, cycle_out)) {
          return true;
        }
      }
      // BLACK: already fully explored, no cycle can pass through it.
    }
  }

  stack.pop_back();
  color[u] = Color::kBlack;
  return false;
}

// O(V + E).
std::vector<std::string> PrereqGraph::FindCycle() const {
  std::unordered_map<std::string, Color> color;
  color.reserve(adj_.size());
  for (const auto& [id, neighbors] : adj_) {
    (void)neighbors;
    color[id] = Color::kWhite;
  }

  // WHY a sorted seed order: hash-map iteration is unspecified, so a graph
  // with multiple cycles could otherwise report a different one between
  // runs. Determinism matters for the grader's reproducibility.
  std::vector<std::string> seeds;
  seeds.reserve(adj_.size());
  for (const auto& [id, neighbors] : adj_) {
    (void)neighbors;
    seeds.push_back(id);
  }
  std::sort(seeds.begin(), seeds.end());

  std::vector<std::string> stack;
  std::vector<std::string> cycle;
  for (const auto& s : seeds) {
    if (color[s] == Color::kWhite) {
      stack.clear();
      if (DfsVisit(s, color, stack, cycle)) {
        return cycle;
      }
    }
  }
  return {};
}
