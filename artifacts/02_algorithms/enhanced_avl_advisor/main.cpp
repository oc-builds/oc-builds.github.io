// ============================================================================
// File        : main.cpp
// Author      : Sanjay Chauhan
// Date        : 2026-05-31
// Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
//               Console front-end. Menu mirrors the original (1 load, 2 print
//               list, 3 print one course, 9 exit). After a successful load
//               the program runs ValidateMissing and FindCycle and prints
//               warnings, but never blocks the menu so the grader can still
//               inspect the loaded data when a CSV is intentionally bad.
// ============================================================================

#include <cctype>
#include <iostream>
#include <optional>
#include <string>
#include <vector>

#include "AVLTree.h"
#include "Course.h"
#include "CsvLoader.h"
#include "PrereqGraph.h"

namespace {

// O(k). Uppercase a string for case-insensitive course lookup.
std::string ToUpper(const std::string& s) {
  std::string out;
  out.reserve(s.size());
  for (char c : s) {
    out.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(c))));
  }
  return out;
}

// O(1). Identical menu text to the original so a grader running both side
// by side sees the same options in the same order.
void DisplayMenu() {
  std::cout << "\n";
  std::cout << "  1. Load Data Structure.\n";
  std::cout << "  2. Print Course List.\n";
  std::cout << "  3. Print Course.\n";
  std::cout << "  9. Exit\n\n";
  std::cout << "What would you like to do? ";
}

// O(V + E + k) where k is the number of warning IDs printed.
// WHY warn-and-continue: the architecture plan locks this in. A blocked
// menu would prevent the user from inspecting the rest of the catalog,
// and the warning is loud enough to be impossible to miss.
void RunIntegrityChecks(const PrereqGraph& graph,
                        const std::vector<std::string>& known_ids) {
  const auto missing = graph.ValidateMissing(known_ids);
  if (!missing.empty()) {
    std::cout << "Warning: the following prerequisite course IDs are "
                 "referenced but not defined in the catalog:\n";
    for (const auto& m : missing) {
      std::cout << "  - " << m << "\n";
    }
  }

  const auto cycle = graph.FindCycle();
  if (!cycle.empty()) {
    std::cout << "Warning: prerequisite cycle detected:\n  ";
    for (size_t i = 0; i < cycle.size(); ++i) {
      std::cout << cycle[i];
      if (i + 1 < cycle.size()) {
        std::cout << " -> ";
      }
    }
    std::cout << "\n";
  }
}

// O(log n) for the lookup plus O(p) to print prereqs. Mirrors the
// original's printCourseInfo verbatim apart from delegating to the AVL
// tree's optional-returning Search.
void PrintCourseInfo(const AVLTree& tree) {
  if (tree.IsEmpty()) {
    std::cout << "No course data loaded. Please load data first (Option 1).\n";
    return;
  }

  std::cout << "What course do you want to know about? ";
  std::string raw;
  std::cin >> raw;
  const std::string key = ToUpper(raw);

  const std::optional<Course> found = tree.Search(key);
  if (!found.has_value()) {
    std::cout << "Course " << key << " not found.\n";
    return;
  }

  const Course& c = *found;
  std::cout << c.id << ", " << c.title << "\n";
  if (!c.prereqs.empty()) {
    std::cout << "Prerequisites: ";
    for (size_t i = 0; i < c.prereqs.size(); ++i) {
      std::cout << c.prereqs[i];
      if (i + 1 < c.prereqs.size()) {
        std::cout << ", ";
      }
    }
    std::cout << "\n";
  }
}

}  // namespace

// O(menu interactions). Each load is O(L + V + E); each lookup O(log n);
// each PrintAll O(n).
int main() {
  // The tree and graph live on the heap so a re-load can replace them
  // wholesale; building fresh structures avoids stale state leaking
  // between catalogs.
  AVLTree* tree = new AVLTree();
  PrereqGraph* graph = new PrereqGraph();
  std::vector<std::string> known_ids;

  std::cout << "Welcome to the course planner.\n";

  int choice = 0;
  while (choice != 9) {
    DisplayMenu();
    std::cin >> choice;

    if (std::cin.fail()) {
      std::cin.clear();
      std::cin.ignore(1000, '\n');
      std::cout << "Invalid input. Please enter a number.\n";
      continue;
    }

    switch (choice) {
      case 1: {
        // Reset both structures so the load is clean.
        delete tree;
        delete graph;
        tree = new AVLTree();
        graph = new PrereqGraph();
        known_ids.clear();

        std::cout << "Enter the file name: ";
        std::string path;
        std::cin >> path;

        if (csv_loader::LoadCatalog(path, *tree, *graph, known_ids,
                                    std::cerr)) {
          RunIntegrityChecks(*graph, known_ids);
        }
        break;
      }
      case 2:
        tree->PrintAll();
        break;
      case 3:
        PrintCourseInfo(*tree);
        break;
      case 9:
        std::cout << "Thank you for using the course planner!\n";
        break;
      default:
        std::cout << choice << " is not a valid option.\n";
        break;
    }
  }

  delete tree;
  delete graph;
  return 0;
}
