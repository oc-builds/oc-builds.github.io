# Publishing this ePortfolio to GitHub Pages

These are the exact steps to publish this site to the user GitHub Pages site at
https://oc-builds.github.io using the account `oc-builds`.

## Before you publish, two reminders

1. Upload the code review video to YouTube, then open `code-review.html` and
   replace the placeholder link. Find the `<a class="video-frame" href="#code-review" ...>`
   element and change its `href` to the YouTube watch URL. The caption below it
   also says TODO: remove that sentence once the link is in.
2. Delete the leftover scratch folder from the artifact staging step. In the
   source artifacts directory there is a folder named `.cs360_polish_trash`
   (outside this site folder, under `CS499/artifacts/`). Remove it so it is not
   part of any future copy. It is not included in this site and does not need to
   ship, but clean it up to keep the source tree tidy.

## One-time setup

For a user site, the repository must be named exactly `oc-builds.github.io`.

1. Create a new repository on GitHub named `oc-builds.github.io` under the
   `oc-builds` account. Make it public.

## Push the site

From inside this `ePortfolio` folder:

```
git init
git add .
git commit -m "Publish CS 499 capstone ePortfolio"
git branch -M main
git remote add origin https://github.com/oc-builds/oc-builds.github.io.git
git push -u origin main
```

## Enable Pages

For a repository named `oc-builds.github.io`, GitHub Pages publishes
automatically from the default branch. To confirm:

1. Go to the repository on GitHub.
2. Open Settings, then Pages.
3. Under Build and deployment, set Source to Deploy from a branch.
4. Set Branch to `main` and the folder to `/ (root)`, then Save.

Wait a minute or two, then visit https://oc-builds.github.io to confirm the site
is live. The `index.html` file at the repository root is served as the home page.

## Updating later

After any edit, run:

```
git add .
git commit -m "Describe the change"
git push
```

Pages rebuilds automatically within a minute or two.
