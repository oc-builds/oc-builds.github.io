// ============================================================================
// File        : AVLTree.cpp
// Author      : Sanjay Chauhan
// Date        : 2026-05-31
// Description : CS499 Enhancement Two rebuild of the CS300 ABCU Course Advisor.
//               AVL tree implementation. Rotation logic follows the textbook
//               four-case scheme (LL, RR, LR, RL). All public methods are
//               thin wrappers around private recursive helpers so the
//               internal Node type never leaks.
// ============================================================================

#include "AVLTree.h"

#include <algorithm>
#include <iostream>
#include <string>
#include <utility>

namespace {

// O(k) where k is the string length. Returns an uppercased copy so the key
// comparison is case-insensitive without mutating the caller's string. Kept
// in an anonymous namespace because it is a translation-unit-local helper.
std::string ToUpper(const std::string& s) {
  std::string out;
  out.reserve(s.size());
  for (char c : s) {
    out.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(c))));
  }
  return out;
}

}  // namespace

// O(1).
AVLTree::AVLTree() : root_(nullptr) {}

// O(n). DestroyTree is post-order so every child is freed before its parent.
AVLTree::~AVLTree() { DestroyTree(root_); }

// O(1).
int AVLTree::Height(const Node* n) { return n == nullptr ? 0 : n->height; }

// O(1).
int AVLTree::BalanceFactor(const Node* n) {
  return n == nullptr ? 0 : Height(n->left) - Height(n->right);
}

// O(1). Recompute height as 1 plus the taller child. Called after every
// structural change because a stale height would break rotation decisions.
void AVLTree::UpdateHeight(Node* n) {
  if (n != nullptr) {
    n->height = 1 + std::max(Height(n->left), Height(n->right));
  }
}

// O(1). Left rotation around n. Used when the right subtree is too tall
// and the imbalance is straight (RR case) or after a right-child right-rotate
// (RL case).
AVLTree::Node* AVLTree::RotateLeft(Node* n) {
  Node* pivot = n->right;
  Node* pivot_left = pivot->left;

  pivot->left = n;
  n->right = pivot_left;

  // Order matters: n is now below pivot, so refresh n first.
  UpdateHeight(n);
  UpdateHeight(pivot);
  return pivot;
}

// O(1). Right rotation around n. Mirror of RotateLeft.
AVLTree::Node* AVLTree::RotateRight(Node* n) {
  Node* pivot = n->left;
  Node* pivot_right = pivot->right;

  pivot->right = n;
  n->left = pivot_right;

  UpdateHeight(n);
  UpdateHeight(pivot);
  return pivot;
}

// O(log n) guaranteed. Recursive descent followed by an O(1) rebalance per
// ancestor. The inserted flag lets the public wrapper report duplicates
// without exceptions.
AVLTree::Node* AVLTree::InsertNode(Node* node, const Course& course,
                                   bool& inserted) {
  if (node == nullptr) {
    inserted = true;
    return new Node(course);
  }

  if (course.id < node->course.id) {
    node->left = InsertNode(node->left, course, inserted);
  } else if (course.id > node->course.id) {
    node->right = InsertNode(node->right, course, inserted);
  } else {
    // Duplicate id: do not insert, matches the original BST's behavior.
    inserted = false;
    return node;
  }

  UpdateHeight(node);

  const int bf = BalanceFactor(node);

  // Left-Left: single right rotation.
  if (bf > 1 && course.id < node->left->course.id) {
    return RotateRight(node);
  }
  // Right-Right: single left rotation.
  if (bf < -1 && course.id > node->right->course.id) {
    return RotateLeft(node);
  }
  // Left-Right: left-rotate the left child, then right-rotate node.
  if (bf > 1 && course.id > node->left->course.id) {
    node->left = RotateLeft(node->left);
    return RotateRight(node);
  }
  // Right-Left: right-rotate the right child, then left-rotate node.
  if (bf < -1 && course.id < node->right->course.id) {
    node->right = RotateRight(node->right);
    return RotateLeft(node);
  }

  return node;
}

// O(log n) guaranteed.
bool AVLTree::Insert(const Course& course) {
  // Normalize the id once so every comparison below is on the canonical key.
  Course normalized = course;
  normalized.id = ToUpper(course.id);

  bool inserted = false;
  root_ = InsertNode(root_, normalized, inserted);
  return inserted;
}

// O(log n) guaranteed. Iterative would also work; recursion is used to match
// the insert path and keep the helper symmetric.
const AVLTree::Node* AVLTree::SearchNode(const Node* node,
                                         const std::string& id) const {
  if (node == nullptr) {
    return nullptr;
  }
  if (id == node->course.id) {
    return node;
  }
  if (id < node->course.id) {
    return SearchNode(node->left, id);
  }
  return SearchNode(node->right, id);
}

// O(log n) guaranteed.
std::optional<Course> AVLTree::Search(const std::string& id) const {
  const std::string key = ToUpper(id);
  const Node* hit = SearchNode(root_, key);
  if (hit == nullptr) {
    return std::nullopt;
  }
  return hit->course;
}

// O(n). Pure in-order walk; each node printed exactly once.
void AVLTree::InOrder(const Node* node) const {
  if (node == nullptr) {
    return;
  }
  InOrder(node->left);
  std::cout << node->course.id << ", " << node->course.title << "\n";
  InOrder(node->right);
}

// O(n).
void AVLTree::PrintAll() const {
  if (root_ == nullptr) {
    std::cout << "No course data loaded. Please load data first (Option 1).\n";
    return;
  }
  std::cout << "Here is a sample schedule:\n\n";
  InOrder(root_);
}

// O(1).
bool AVLTree::IsEmpty() const { return root_ == nullptr; }

// O(n). Post-order so children are released before their parent pointer
// is invalidated.
void AVLTree::DestroyTree(Node* node) {
  if (node == nullptr) {
    return;
  }
  DestroyTree(node->left);
  DestroyTree(node->right);
  delete node;
}
