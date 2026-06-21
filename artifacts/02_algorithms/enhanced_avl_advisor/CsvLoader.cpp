// ============================================================================
// File        : CsvLoader.cpp
// Author      : Sanjay Chauhan
// Date        : 2026-05-31
// Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
//               CsvLoader implementation. Pass 1 builds Course records and
//               inserts them into the tree while registering graph nodes;
//               pass 2 walks the captured records and adds prerequisite
//               edges. Both passes run inside one function call so the
//               caller never sees a half-loaded state.
// ============================================================================

#include "CsvLoader.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "Course.h"

namespace csv_loader {

namespace {

// O(k). Strip a single trailing \r and any surrounding ASCII whitespace.
// WHY: the original CSV ships with Windows line endings on some checkouts
// and a stray space in a course ID would silently create a phantom course
// the user could never look up.
std::string Trim(const std::string& in) {
  size_t start = 0;
  size_t end = in.size();
  while (start < end &&
         std::isspace(static_cast<unsigned char>(in[start]))) {
    ++start;
  }
  while (end > start &&
         std::isspace(static_cast<unsigned char>(in[end - 1]))) {
    --end;
  }
  return in.substr(start, end - start);
}

// O(k). Uppercase copy. Duplicated from AVLTree.cpp's local helper because
// crossing a translation-unit boundary just to share four lines would
// couple unrelated modules.
std::string ToUpper(const std::string& s) {
  std::string out;
  out.reserve(s.size());
  for (char c : s) {
    out.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(c))));
  }
  return out;
}

}  // namespace

// O(L + V + E).
bool LoadCatalog(const std::string& path, AVLTree& tree, PrereqGraph& graph,
                 std::vector<std::string>& known_ids, std::ostream& err) {
  known_ids.clear();
  std::ifstream in(path);
  if (!in.is_open()) {
    err << "Error: Could not open file \"" << path << "\".\n";
    return false;
  }

  // Pass 1: parse every line into a Course, insert into the tree, register
  // each course id as a graph node. We hold the parsed records in a local
  // vector so pass 2 does not have to re-read the file or re-tokenize.
  std::vector<Course> records;
  std::string line;
  int line_no = 0;

  while (std::getline(in, line)) {
    ++line_no;

    // Strip CR for Windows line endings before trimming, so a line that is
    // just "\r" collapses to empty and is skipped.
    if (!line.empty() && line.back() == '\r') {
      line.pop_back();
    }
    if (Trim(line).empty()) {
      continue;
    }

    std::stringstream ss(line);
    std::string token;
    std::vector<std::string> tokens;
    while (std::getline(ss, token, ',')) {
      tokens.push_back(Trim(token));
    }

    if (tokens.size() < 2 || tokens[0].empty() || tokens[1].empty()) {
      err << "Warning: skipping malformed line " << line_no << ": " << line
          << "\n";
      continue;
    }

    Course c;
    c.id = ToUpper(tokens[0]);
    c.title = tokens[1];
    for (size_t i = 2; i < tokens.size(); ++i) {
      if (!tokens[i].empty()) {
        c.prereqs.push_back(ToUpper(tokens[i]));
      }
    }

    if (!tree.Insert(c)) {
      err << "Warning: duplicate course id on line " << line_no << ": "
          << c.id << " (kept first occurrence)\n";
      continue;
    }
    graph.AddNode(c.id);
    known_ids.push_back(c.id);
    records.push_back(std::move(c));
  }

  // Pass 2: every known id is now a graph node. Add edges for each
  // (course, prereq) pair. If the prereq is unknown, the edge is still
  // added so ValidateMissing can report it; FindCycle skips edges with no
  // registered target so a typo cannot fake a cycle.
  for (const auto& c : records) {
    for (const auto& p : c.prereqs) {
      graph.AddEdge(c.id, p);
    }
  }

  std::cout << records.size() << " courses loaded.\n";
  return true;
}

}  // namespace csv_loader
