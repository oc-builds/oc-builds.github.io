# Sanjay Chauhan, CS 499 Computer Science Capstone ePortfolio

This repository is the ePortfolio for my CS 499 Computer Science Capstone at
Southern New Hampshire University. It is a static, multi-page website built with
plain HTML5 and CSS, with no build step and no JavaScript dependency, so it runs
the same locally and on GitHub Pages.

## Live site

https://oc-builds.github.io

## What is here

- `index.html` is the landing page and carries the full professional
  self-assessment, which is the centerpiece of the portfolio.
- `code-review.html` holds the recorded code review walkthrough.
- `artifact-software-design.html`, `artifact-algorithms.html`, and
  `artifact-databases.html` are one page per enhanced artifact, each with a
  before-and-after code treatment, the full enhancement narrative, links to the
  real source code, and the course outcomes it supports.
- `outcomes.html` maps the five course outcomes to concrete evidence.
- `styles.css` is the single shared stylesheet.
- `artifacts/` contains clean copies of the original and enhanced source code for
  all three artifacts, organized as `01_software_design`, `02_algorithms`, and
  `03_databases`.

## The three artifacts

1. Software design and engineering, CS 360. An Android inventory app rebuilt as a
   React, Node, Express, and SQLite full-stack web application with JWT and
   bcrypt authentication, role-based access control, and a service-layer
   architecture.
2. Algorithms and data structures, CS 300. A C++ course advisor rebuilt with a
   self-balancing AVL tree, a directed prerequisite graph, and three-color
   depth-first cycle detection.
3. Databases, CS 340. A Jupyter and PyMongo project rebuilt as a FastAPI and
   MongoDB 7 service with schema validation, deliberate indexing, GeoJSON, and an
   audit log.

## Viewing locally

Open `index.html` in any web browser, or serve the folder with a simple static
server, for example `python3 -m http.server` from this directory and then open
http://localhost:8000.
