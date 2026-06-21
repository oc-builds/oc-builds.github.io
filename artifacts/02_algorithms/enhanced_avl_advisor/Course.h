// ============================================================================
// File        : Course.h
// Author      : Sanjay Chauhan
// Date        : 2026-05-31
// Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
//               Plain-data Course record shared by the AVL tree, the
//               prerequisite graph, and the CSV loader. Kept header-only and
//               dependency-free so the storage layer (AVLTree) and the
//               relationship layer (PrereqGraph) can include it without
//               pulling in each other's headers.
// ============================================================================

#ifndef COURSE_H_
#define COURSE_H_

#include <string>
#include <vector>

// A single course record. Field names match the original ProjectTwo.cpp
// semantics but are renamed to Google C++ Style snake_case-with-no-underscore
// for the simple members. The id is stored uppercased so the AVL tree's
// ordering and the graph's adjacency keys agree regardless of how the user
// typed the course ID at the prompt.
struct Course {
  std::string id;                      // unique course identifier, uppercased
  std::string title;                   // human-readable course title
  std::vector<std::string> prereqs;    // uppercased prerequisite IDs
};

#endif  // COURSE_H_
