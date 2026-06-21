// ============================================================================
// File        : AVLTree.h
// Author      : Sanjay Chauhan
// Date        : 2026-05-31
// Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
//               Self-balancing AVL tree of Course records keyed by Course.id.
//
//               WHY AVL over the original plain BST: a course catalog exported
//               from a registrar or sorted alphabetically by tooling is a
//               realistic adversarial input. A plain BST fed sorted keys
//               degenerates into a linked list and forces O(n) insert and
//               search. AVL maintains the balance-factor invariant |bf| <= 1
//               at every node via rotations, so insert and search are
//               O(log n) guaranteed, independent of insertion order.
// ============================================================================

#ifndef AVLTREE_H_
#define AVLTREE_H_

#include <optional>
#include <string>

#include "Course.h"

class AVLTree {
 public:
  // O(1). Constructs an empty tree.
  AVLTree();

  // O(n). Post-order recursive teardown of every owned node.
  ~AVLTree();

  // Non-copyable. The tree owns raw pointers and a shallow copy would
  // double-free; a deep copy is not needed by the advisor and would only
  // hide bugs if added later.
  AVLTree(const AVLTree&) = delete;
  AVLTree& operator=(const AVLTree&) = delete;

  // O(log n) guaranteed. Inserts course keyed by an uppercased copy of
  // course.id. Returns true if inserted, false if a course with the same id
  // already exists (matches the original BST's no-duplicate behavior).
  bool Insert(const Course& course);

  // O(log n) guaranteed. Returns the course if found, std::nullopt otherwise.
  // The lookup key is uppercased before comparison so callers can pass any
  // case (mirrors the case-insensitive prompt behavior of the original).
  std::optional<Course> Search(const std::string& id) const;

  // O(n). In-order traversal prints every course in ascending id order to
  // std::cout in the same "ID, Title" format the original used.
  void PrintAll() const;

  // O(1). True when no courses have been loaded.
  bool IsEmpty() const;

 private:
  // Internal node. Kept private so no raw pointer ever escapes the class.
  struct Node {
    Course course;
    Node* left;
    Node* right;
    int height;  // height of subtree rooted here; leaf height is 1

    explicit Node(const Course& c)
        : course(c), left(nullptr), right(nullptr), height(1) {}
  };

  Node* root_;

  // O(1). Null-safe height lookup so callers do not have to branch.
  static int Height(const Node* n);

  // O(1). left height minus right height; positive means left-heavy.
  static int BalanceFactor(const Node* n);

  // O(1). Refresh height from children. Called after every structural change.
  static void UpdateHeight(Node* n);

  // O(1). Single rotations. Each fixes one of the four imbalance cases.
  // The double-rotation cases (LR, RL) are handled inline in Insert by
  // composing these primitives, which is the standard textbook approach.
  static Node* RotateLeft(Node* n);
  static Node* RotateRight(Node* n);

  // O(log n) guaranteed. Recursive insert helper. Rebalances on the way
  // back up the recursion so each ancestor is checked exactly once.
  // Sets inserted to false when a duplicate id is encountered so the
  // public Insert can report it without throwing.
  Node* InsertNode(Node* node, const Course& course, bool& inserted);

  // O(log n) guaranteed. Recursive search helper. Returns nullptr if absent.
  const Node* SearchNode(const Node* node, const std::string& id) const;

  // O(n). In-order print helper. Pure traversal, no balance work.
  void InOrder(const Node* node) const;

  // O(n). Post-order delete helper. Children freed before parent so no
  // pointer is ever read after being deleted.
  void DestroyTree(Node* node);
};

#endif  // AVLTREE_H_
