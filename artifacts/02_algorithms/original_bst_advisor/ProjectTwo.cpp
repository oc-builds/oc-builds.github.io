//============================================================================
// Name        : ProjectTwo.cpp
// Author      : Sanjay Chauhan
// Version     : 1.0
// Description : ABCU Advising Assistance Program
//               Uses a Binary Search Tree (BST) to store and retrieve
//               course information for the CS department advising team.
//               BST was chosen because sorted output (Option 2) is a core
//               requirement, and in-order traversal produces alphanumeric
//               order in O(n) without needing a separate sort step.
//============================================================================

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

//============================================================================
// Course structure to hold course data
//============================================================================

struct Course {
    string courseNumber;           // unique identifier (e.g., "CSCI300")
    string title;                  // course title (e.g., "Introduction to Algorithms")
    vector<string> prerequisites;  // list of prerequisite course numbers
};

//============================================================================
// BST Node structure
//============================================================================

struct Node {
    Course course;
    Node* left;   // pointer to left child (smaller courseNumber)
    Node* right;  // pointer to right child (larger courseNumber)

    // Constructor initializes children to nullptr
    Node(Course aCourse) : course(aCourse), left(nullptr), right(nullptr) {}
};

//============================================================================
// Binary Search Tree class definition
//============================================================================

class BinarySearchTree {
private:
    Node* root;  // pointer to the root node of the tree

    /**
     * Recursively insert a course into the subtree rooted at node.
     * BST invariant: left < node < right (compared by courseNumber).
     *
     * @param node current subtree root
     * @param course the course to insert
     * @return the (possibly updated) subtree root
     */
    Node* insertNode(Node* node, Course course) {
        // Base case: empty spot found, create new node here
        if (node == nullptr) {
            return new Node(course);
        }

        // Compare course numbers to decide left or right
        if (course.courseNumber < node->course.courseNumber) {
            node->left = insertNode(node->left, course);
        } else if (course.courseNumber > node->course.courseNumber) {
            node->right = insertNode(node->right, course);
        }
        // If equal, course already exists; do not insert duplicate

        return node;
    }

    /**
     * Recursively search for a course by courseNumber.
     * Follows BST property: go left if target is smaller, right if larger.
     *
     * @param node current subtree root
     * @param courseNumber the course number to find
     * @return pointer to the node if found, nullptr otherwise
     */
    Node* searchNode(Node* node, const string& courseNumber) const {
        // Base case: not found or found
        if (node == nullptr) {
            return nullptr;
        }

        if (courseNumber == node->course.courseNumber) {
            return node;
        } else if (courseNumber < node->course.courseNumber) {
            return searchNode(node->left, courseNumber);
        } else {
            return searchNode(node->right, courseNumber);
        }
    }

    /**
     * In-order traversal: visit left, print current, visit right.
     * This produces courses in alphanumeric order because the BST
     * invariant guarantees left < current < right at every node.
     * Runs in O(n) time, visiting each node exactly once.
     *
     * @param node current subtree root
     */
    void inOrder(Node* node) const {
        if (node == nullptr) {
            return;
        }

        inOrder(node->left);
        cout << node->course.courseNumber << ", " << node->course.title << endl;
        inOrder(node->right);
    }

    /**
     * Post-order traversal to delete all nodes.
     * Visits children before parent so no dangling pointers remain.
     *
     * @param node current subtree root
     */
    void destroyTree(Node* node) {
        if (node == nullptr) {
            return;
        }

        destroyTree(node->left);
        destroyTree(node->right);
        delete node;
    }

public:
    // Constructor: start with empty tree
    BinarySearchTree() : root(nullptr) {}

    // Destructor: free all nodes using post-order traversal
    ~BinarySearchTree() {
        destroyTree(root);
    }

    /**
     * Public insert: adds a course to the BST.
     * Worst case O(n) if tree becomes unbalanced (e.g., sorted input).
     * Average case O(log n) for a reasonably balanced tree.
     *
     * @param course the course to insert
     */
    void Insert(Course course) {
        root = insertNode(root, course);
    }

    /**
     * Public search: finds a course by courseNumber.
     * Returns an empty Course if not found.
     * Worst case O(n) for a degenerate (unbalanced) tree.
     * Average case O(log n) for a balanced tree.
     *
     * @param courseNumber the course number to search for
     * @return the matching Course, or empty Course if not found
     */
    Course Search(const string& courseNumber) const {
        // Convert to uppercase for case-insensitive search
        string upperKey = courseNumber;
        transform(upperKey.begin(), upperKey.end(), upperKey.begin(), ::toupper);

        Node* result = searchNode(root, upperKey);

        if (result != nullptr) {
            return result->course;
        }

        // Not found: return empty course
        Course emptyCourse;
        return emptyCourse;
    }

    /**
     * Check if the tree is empty (no courses loaded).
     *
     * @return true if the tree has no nodes
     */
    bool IsEmpty() const {
        return root == nullptr;
    }

    /**
     * Public print: prints all courses in alphanumeric order
     * using in-order traversal. O(n) time.
     */
    void PrintAll() const {
        if (root == nullptr) {
            cout << "No course data loaded. Please load data first (Option 1)." << endl;
            return;
        }

        cout << "Here is a sample schedule:" << endl;
        cout << endl;
        inOrder(root);
    }
};

//============================================================================
// File loading function
//============================================================================

/**
 * Load course data from a CSV file into the BST.
 * Format: courseNumber,title,prereq1,prereq2,...
 * Each line must have at least 2 fields (courseNumber and title).
 *
 * @param filePath path to the CSV file
 * @param bst pointer to the BST to populate
 * @return true if file loaded successfully, false otherwise
 */
bool loadDataStructure(const string& filePath, BinarySearchTree* bst) {
    ifstream inFile(filePath);

    // Check if file opened successfully
    if (!inFile.is_open()) {
        cout << "Error: Could not open file \"" << filePath << "\"." << endl;
        return false;
    }

    string line;
    int lineCount = 0;

    while (getline(inFile, line)) {
        // Skip empty lines
        if (line.empty()) {
            continue;
        }

        // Remove trailing carriage return if present (Windows line endings)
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }

        stringstream ss(line);
        string token;
        vector<string> tokens;

        // Parse comma-separated values
        while (getline(ss, token, ',')) {
            tokens.push_back(token);
        }

        // Validate: must have at least courseNumber and title
        if (tokens.size() < 2) {
            cout << "Warning: Skipping malformed line: " << line << endl;
            continue;
        }

        // Build course object
        Course course;
        course.courseNumber = tokens[0];
        course.title = tokens[1];

        // Add any prerequisites (tokens at index 2 and beyond)
        for (unsigned int i = 2; i < tokens.size(); ++i) {
            if (!tokens[i].empty()) {
                course.prerequisites.push_back(tokens[i]);
            }
        }

        // Insert into BST
        bst->Insert(course);
        lineCount++;
    }

    inFile.close();
    cout << lineCount << " courses loaded." << endl;
    return true;
}

//============================================================================
// Print individual course information
//============================================================================

/**
 * Prompt user for a course number, search the BST, and print
 * the course title and prerequisites if found.
 *
 * @param bst pointer to the BST
 */
void printCourseInfo(BinarySearchTree* bst) {
    // Check if data has been loaded before prompting
    if (bst->IsEmpty()) {
        cout << "No course data loaded. Please load data first (Option 1)." << endl;
        return;
    }

    string courseNumber;
    cout << "What course do you want to know about? ";
    cin >> courseNumber;

    // Convert to uppercase for case-insensitive lookup
    transform(courseNumber.begin(), courseNumber.end(), courseNumber.begin(), ::toupper);

    Course course = bst->Search(courseNumber);

    // Check if course was found (empty courseNumber means not found)
    if (course.courseNumber.empty()) {
        cout << "Course " << courseNumber << " not found." << endl;
    } else {
        // Print course number and title
        cout << course.courseNumber << ", " << course.title << endl;

        // Print prerequisites if any exist
        if (!course.prerequisites.empty()) {
            cout << "Prerequisites: ";
            for (unsigned int i = 0; i < course.prerequisites.size(); ++i) {
                cout << course.prerequisites[i];
                if (i < course.prerequisites.size() - 1) {
                    cout << ", ";
                }
            }
            cout << endl;
        }
    }
}

//============================================================================
// Display menu
//============================================================================

void displayMenu() {
    cout << endl;
    cout << "  1. Load Data Structure." << endl;
    cout << "  2. Print Course List." << endl;
    cout << "  3. Print Course." << endl;
    cout << "  9. Exit" << endl;
    cout << endl;
    cout << "What would you like to do? ";
}

//============================================================================
// Main program
//============================================================================

int main() {
    BinarySearchTree* bst = new BinarySearchTree();
    string filePath;
    int choice = 0;

    cout << "Welcome to the course planner." << endl;

    // Main program loop
    while (choice != 9) {
        displayMenu();
        cin >> choice;

        // Handle invalid input (non-integer)
        if (cin.fail()) {
            cin.clear();
            cin.ignore(1000, '\n');
            cout << "Invalid input. Please enter a number." << endl;
            continue;
        }

        switch (choice) {
            case 1:
                // Load data from file into BST
                cout << "Enter the file name: ";
                cin >> filePath;
                loadDataStructure(filePath, bst);
                break;

            case 2:
                // Print sorted course list via in-order traversal
                bst->PrintAll();
                break;

            case 3:
                // Print individual course info
                printCourseInfo(bst);
                break;

            case 9:
                // Exit
                cout << "Thank you for using the course planner!" << endl;
                break;

            default:
                // Invalid menu option
                cout << choice << " is not a valid option." << endl;
                break;
        }
    }

    // Clean up
    delete bst;

    return 0;
}
