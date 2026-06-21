// ============================================================================
// File        : PrereqGraph.h
// Author      : Sanjay Chauhan
// Date        : 2026-05-31
// Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
//               Directed graph of course prerequisite relationships, used for
//               (a) validating that every referenced prerequisite is itself a
//               course in the catalog and (b) detecting circular dependency
//               chains via three-color depth-first search.
//
//               WHY: the original advisor stored prerequisites as raw strings
//               and never checked them. A registrar typo or a malformed
//               degree plan that loops back on itself would load silently and
//               present nonsense advice to a student. The graph turns the
//               problem into a classic O(V + E) traversal that is both fast
//               and easy to reason about for the grader.
// ============================================================================

#ifndef PREREQGRAPH_H_
#define PREREQGRAPH_H_

#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

class PrereqGraph {
 public:
  // O(1). Empty graph.
  PrereqGraph() = default;

  // O(1) amortized. Adds an isolated node for id. No-op if id is already
  // present, which lets callers add the same id twice without a guard.
  void AddNode(const std::string& id);

  // O(1) amortized. Adds a directed edge from -> to. Does not auto-create
  // missing endpoints because the loader's two-pass design guarantees both
  // endpoints already exist as nodes by the time edges are added; missing
  // endpoints are detected separately by ValidateMissing.
  void AddEdge(const std::string& from, const std::string& to);

  // O(V + E). Returns the set of prerequisite IDs that were referenced as
  // edge targets but were never registered as their own course (i.e., a
  // dangling reference). known_ids is the authoritative course set the
  // loader built; anything pointed to but not in this set is reported.
  std::vector<std::string> ValidateMissing(
      const std::vector<std::string>& known_ids) const;

  // O(V + E). Three-color DFS. Returns the IDs that participate in one
  // discovered cycle, in the order they appear along the cycle, or an empty
  // vector if the graph is acyclic. Only one cycle is reported because that
  // is enough to prove the catalog is invalid and the user needs to fix the
  // CSV before further analysis adds value.
  std::vector<std::string> FindCycle() const;

 private:
  // WHY unordered_map: O(1) amortized lookup keyed by string is exactly the
  // operation pattern of every method below, and the iteration order is
  // never exposed to the user (the AVL tree handles ordered output).
  std::unordered_map<std::string, std::vector<std::string>> adj_;

  // DFS coloring for cycle detection. WHITE = untouched, GRAY = on current
  // recursion stack, BLACK = fully explored. Encountering a GRAY successor
  // proves a back-edge, which proves a cycle.
  enum class Color { kWhite, kGray, kBlack };

  // O(deg(u) + descendants). Recursive DFS helper. On detecting a back edge
  // it unwinds the recursion stack into cycle_out and returns true so the
  // caller can short-circuit further work.
  bool DfsVisit(const std::string& u,
                std::unordered_map<std::string, Color>& color,
                std::vector<std::string>& stack,
                std::vector<std::string>& cycle_out) const;
};

#endif  // PREREQGRAPH_H_
