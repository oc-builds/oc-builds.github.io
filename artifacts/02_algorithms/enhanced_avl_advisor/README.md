# ABCU Course Advisor, Enhanced (CS499 Enhancement Two)

C++17 rebuild of the CS300 ABCU Advising Program. Replaces the original plain BST with a self-balancing AVL tree and adds a directed prerequisite graph with DFS-based cycle detection and missing-prereq validation.

## What changed from the original

| Concern | Original (`ProjectTwo.cpp`) | Enhanced |
|---|---|---|
| Storage | Plain BST, O(n) worst case on sorted input | AVL tree, O(log n) guaranteed |
| Prerequisite validation | None | Cross-checked against the catalog |
| Cycle detection | None | DFS three-color, O(V + E) |
| File layout | One 397-line file | Five small modules + Course header |
| Style | Mixed | Google C++ Style, no `using namespace std;` in headers |

## How to build

### With make (Linux / macOS)

```
make
```

### One-line g++ fallback (Windows graders, no make)

```
g++ -std=c++17 *.cpp -o advisor
```

Either approach produces an executable named `advisor` (or `advisor.exe` on Windows).

## How to run

```
./advisor
```

The menu is identical to the original:

```
  1. Load Data Structure.
  2. Print Course List.
  3. Print Course.
  9. Exit
```

When prompted for a file name, supply one of the CSVs in this folder.

## CSV files included

| File | Purpose |
|---|---|
| `ABCU_Advising_Program_Input.csv` | Original 8-course catalog. Loads cleanly with no warnings. |
| `ABCU_Advising_Program_Input_Sorted.csv` | Same 8 courses sorted by course ID. Demonstrates the AVL advantage, the original plain BST would degenerate to a linked list on this ordering. |
| `ABCU_Advising_Program_Input_BadCycle.csv` | Contains a circular prerequisite chain. Proves cycle detection fires and warns the user. |
| `ABCU_Advising_Program_Input_MissingPrereq.csv` | References a non-existent course. Proves the missing-prereq validator fires. |

## CSV format

```
COURSE_ID,Title,Prereq1,Prereq2,...
```

- `COURSE_ID` is a unique identifier (e.g., `CSCI300`). Stored uppercased; lookup is case-insensitive.
- `Title` is human-readable.
- Zero or more prerequisite IDs follow, comma-separated.
- Empty trailing fields (`,,`) are ignored.

## File layout

```
enhanced_avl_advisor/
  Course.h              -- Course struct (id, title, prereqs)
  AVLTree.h / .cpp      -- Self-balancing AVL tree, keyed by course id
  PrereqGraph.h / .cpp  -- Directed graph + three-color DFS cycle detection
  CsvLoader.h / .cpp    -- Two-pass CSV parser
  main.cpp              -- Menu driver
  Makefile              -- `make` and `make clean`
  README.md             -- This file
  *.csv                 -- Four input catalogs (see table above)
```

## Big-O summary

| Operation | Complexity | Notes |
|---|---|---|
| AVL Insert | O(log n) guaranteed | Rotations keep |bf| <= 1 |
| AVL Search | O(log n) guaranteed | Same reason |
| AVL PrintAll | O(n) | In-order walk |
| Graph AddNode | O(1) amortized | Hash map insert |
| Graph AddEdge | O(1) amortized | Vector push_back |
| ValidateMissing | O(V + E) | One pass over adjacency lists |
| FindCycle | O(V + E) | Three-color DFS |

## Author

Sanjay Chauhan, CS499 Capstone, SNHU, 2026-05-31.
