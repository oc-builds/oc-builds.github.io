// ============================================================================
// File        : CsvLoader.h
// Author      : Sanjay Chauhan
// Date        : 2026-05-31
// Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
//               Loads the ABCU CSV into both the AVL tree and the prereq
//               graph in one call. Two-pass so the graph can reject
//               dangling references after every ID is known.
// ============================================================================

#ifndef CSVLOADER_H_
#define CSVLOADER_H_

#include <ostream>
#include <string>
#include <vector>

#include "AVLTree.h"
#include "PrereqGraph.h"

namespace csv_loader {

// O(L + V + E) where L is line count.
//
// Pass 1: read every line, build a Course, insert into the tree, register
// the id as a graph node, and append the id to known_ids.
//
// Pass 2: walk the parsed records and AddEdge for each (course, prereq)
// pair. The two-pass design is required because the original CSV
// forward-references CSCI200 from CSCI300 before CSCI200's own row is
// reached; a one-pass loader would have to either delay edge insertion or
// register nodes lazily, both of which would muddle the "validate against
// the known set" check that runs in main.
//
// known_ids is cleared at entry and then filled with every successfully
// inserted course ID. The caller hands it to PrereqGraph::ValidateMissing
// so the validator has the authoritative set without the graph needing to
// expose its internal adjacency keys.
//
// Returns true if the file opened (an empty file still returns true with
// zero courses loaded); false on open failure.
bool LoadCatalog(const std::string& path, AVLTree& tree, PrereqGraph& graph,
                 std::vector<std::string>& known_ids, std::ostream& err);

}  // namespace csv_loader

#endif  // CSVLOADER_H_
