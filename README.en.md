<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="hxz-content-reach: turn Xiaohongshu and Douyin video links into your Feishu content library, one row per video">
</p>

<p align="center"><a href="./README.md">简体中文</a> · <b>English</b></p>

**Turn Xiaohongshu and Douyin videos into your own Feishu content library.**

When you find a video worth keeping, you don't have to copy the script, save the cover, or move the numbers by hand. Send one link in Hermes, and it turns the video into text and saves it — together with the cover, the author, and the engagement numbers — into the Feishu Base table you chose.

> The images on this page are in Chinese; the text around them explains the same content.

## See what you get first

One video becomes one row in your table:

<p align="center">
  <img src="./assets/readme/output-preview.svg" width="100%" alt="Example row with made-up data: cover, title, platform, author, type, publish date, likes, saves, comments, shares, a transcript excerpt, tags, video link, collected-at time and remark">
</p>

- **Full transcript**: the spoken audio turned into text, with punctuation and paragraphs, easy to read, search, and quote.
- **Original cover**: the cover the creator set, kept at its original aspect ratio.
- **Source details**: title, author, platform, type (e.g. video), publish date, and the original link, so you can go back to the video.
- **Engagement numbers**: likes, saves, comments, shares, plus the time they were collected.
- **Content tags**: to help you organize the library.

It suits people who use videos as topic references, study material, or source material. It collects and organizes; it does not rewrite videos into original articles for you.

## Already set up? Just do this

In the Hermes chat box, send:

```text
/hxz-content-reach <paste a Xiaohongshu or Douyin video link>
```

Share text copied from the app works too:

```text
/hxz-content-reach <paste the whole share text>
```

Wait for Hermes to say the row has been saved, then open your own Feishu table. You don't need to download the video, tidy up the transcript, or upload the cover yourself.

<p align="center">
  <img src="./assets/readme/workflow.svg" width="100%" alt="What happens after you send a link: send link, collect the page, check for duplicates, transcribe locally and add punctuation, write to Feishu and read it back to confirm; if the video is already in the table, only the engagement numbers and collected-at time are updated">
</p>

**Sending the same video again does not create a duplicate row.** It only updates the engagement numbers visible this time and the collection time.

If you only want to look and not write to the table, say so explicitly:

```text
/hxz-content-reach <video link> Just show me, don't save it.
```

## First time: let Hermes get you ready

You need three things:

1. **Hermes Agent**: to install and run this Skill.
2. **A Feishu account and a library table**: to store what gets collected.
3. **A Chrome browser that can open the videos**: if a login is needed, you sign in yourself.

After installing the Skill, send the message below to Hermes, along with the link to your own Feishu table:

```text
I want to start using hxz-content-reach.
Here is my Feishu Base table: <paste table link>.
Please check the table fields and this computer's environment, and finish the setup needed.
Before installing software or downloading models, tell me what it's for, where it will be saved, and what I need to confirm.
I'll handle logins and authorization myself; please do every other step you can.
When it's ready, I'll send one video link to try it.
```

This is a request for an Agent to help you set up, not a one-click installer. The first run needs a local transcription model and a punctuation model; see [docs/INSTALL.md](./docs/INSTALL.md) for the installation details. Day-to-day use doesn't require touching these tools again.

If you don't have a library table yet, tell Hermes first:

```text
I don't have a Feishu library table yet. Please design and create one that fits hxz-content-reach.
```

Confirm the fields and permissions before a new table is created. Suggested fields: title, platform, author, cover, transcript, type, tags, publish date, video link, likes, saves, comments, shares, collected at, and remark.

## Try your first video

Pick a short video you are allowed to process and that plays normally, then send:

```text
/hxz-content-reach <video link>
```

When it finishes, check just three things:

- the row appears in Feishu;
- the cover and source match the video;
- the transcript reads normally.

If something goes wrong, leave Hermes's message in the chat as is and let it keep investigating from there. You don't need to understand the technical error yourself.

## Know these before you start

- **The transcript is not human-proofread**: by default it is transcribed and punctuated on your computer, so names and sound-alike words may be wrong. Check against the original video before quoting it formally; ask explicitly if you want further proofreading.
- **Covers keep their original ratio**: if the creator used a landscape cover, it is saved as landscape, not cropped to portrait.
- **Engagement numbers are a snapshot at collection time**: later changes on the platform are not synced automatically; collect again to update them.
- **Only process content you are allowed to process**: logins, resource permissions, and platform access rules still apply.

## Project status

An engineering version organized for personal use; licensing is pending confirmation. See [docs/PROVENANCE.md](./docs/PROVENANCE.md).

## Docs

- Installation and dependencies: [docs/INSTALL.md](./docs/INSTALL.md)
- Configuration, item by item: [docs/CONFIGURATION.md](./docs/CONFIGURATION.md)
- Components and data flow: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- Acceptance and recovery commands: [docs/VERIFICATION.md](./docs/VERIFICATION.md)
- Origin and licensing: [docs/PROVENANCE.md](./docs/PROVENANCE.md)

For contributing see [CONTRIBUTING.md](./CONTRIBUTING.md), for security issues see [SECURITY.md](./SECURITY.md), and for changes see [CHANGELOG.md](./CHANGELOG.md).

<sub>The linked docs are currently written in Chinese.</sub>
