# Setup: connect YouTube and Facebook (one time, ~30–60 min)

The workflow already runs without keys: it makes the video and keeps it as a download (Actions → run → *Artifacts*).
Add the keys below and it will also upload. **Keys go only into GitHub Secrets — never into files or chats.**

GitHub → this repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | What it is |
|---|---|
| `YT_CLIENT_ID` | Google OAuth client ID |
| `YT_CLIENT_SECRET` | Google OAuth client secret |
| `YT_REFRESH_TOKEN` | Long-lived token for your channel (from `scripts/get_youtube_token.py`) |
| `FB_PAGE_ID` | Your Facebook Page ID |
| `FB_PAGE_TOKEN` | A long-lived **Page** access token |
| `TT_CLIENT_KEY`, `TT_CLIENT_SECRET` | TikTok app keys (optional, section 2c) |
| `TT_REFRESH_TOKEN`, `TT_TOKEN_KEY` | From `scripts/get_tiktok_token.py` (optional, section 2c) |

---

## 1. YouTube

1. Go to <https://console.cloud.google.com/> → create a project, e.g. `daily-english`.
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **APIs & Services → OAuth consent screen** → User type **External** → fill in app name and your email.
   - Add yourself under **Test users**.
   - Then **Publish app** (switch from *Testing* to *In production*). In *Testing* mode the refresh token expires after 7 days.
   - You'll see "unverified app" warnings when you sign in — that's fine for your own use (click *Advanced → continue*).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID** → type **Desktop app** → download the JSON.
5. On your computer, in this repo:
   ```bash
   pip install google-auth-oauthlib
   python scripts/get_youtube_token.py ~/Downloads/client_secret_xxx.json
   ```
   A browser opens. Sign in, and **pick the Daily English channel (Brand Account)**, not your personal channel.
   It prints the three values → add them as secrets. Then delete the downloaded JSON or keep it private.

**Important:** until Google audits your API project, YouTube may lock API uploads to **private**.
If videos stay private: either publish them by hand in YouTube Studio, or fill in the
**YouTube API Services – Audit and Quota Extension Form** (search that name; it's linked from Google's YouTube API "Quota and Compliance Audits" page) (free; takes time).

## 2. Facebook Page

1. Go to <https://developers.facebook.com/apps> → **Create app** → type **Business** (or "Other → Business").
2. Open **Graph API Explorer** (<https://developers.facebook.com/tools/explorer/>):
   - Select your app, then **User or Page → Get Page Access Token**.
   - Permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
   - Choose the **Daily English** page.
3. Make it **long-lived**:
   - Get a long-lived *user* token at **Access Token Debugger** (<https://developers.facebook.com/tools/debug/accesstoken/>) → *Extend Access Token*.
   - In Graph API Explorer, with that long-lived user token, call `me/accounts` → copy your page's `access_token` and `id`.
   - A page token made from a long-lived user token does not expire (until you change your password or remove the app).
4. Add `FB_PAGE_ID` and `FB_PAGE_TOKEN` as secrets.

## 2b. Instagram (optional)

Uses the same `FB_PAGE_ID` / `FB_PAGE_TOKEN` — no new secrets.

1. Your Instagram must be a **Professional** account (Business or Creator) **linked to the Facebook Page**.
2. Meta app → **Use cases → Add** → **Manage messaging & content on Instagram** → *API setup with Facebook login*.
3. Generate the Page token again with `instagram_basic` and `instagram_content_publish` added (choose the Page **and** the Instagram account in the pop-up), and update `FB_PAGE_TOKEN`.

Instagram's API can't schedule posts, so the night runs upload the Reels and **Publish Instagram**
(11:47 and 17:47 Vietnam time) publishes them. Instagram's "AI info" label is added (set `IG_AI_LABEL: "false"` in the workflow env to turn it off).


## 2c. TikTok (optional, drafts to your inbox)

TikTok only lets apps post **publicly** after a full review, so this uses the lighter
**"upload a draft"** permission: each video arrives in your TikTok app as a notification,
you open it, paste the caption and tap **Post** (about 30 seconds).

1. Have a TikTok account for Daily English (log in to it in the TikTok app on your phone).
2. Go to <https://developers.tiktok.com/> → log in → **Manage apps → Connect an app** (create an app).
   Fill in:
   - App name `Daily English uploader`, category **Education**, an icon (your channel logo).
   - Description: *Private tool that sends my own Daily English vocabulary videos to my TikTok inbox as drafts. I review and post each one myself in the TikTok app.*
   - **Terms of Service URL**: `https://phongmanh.github.io/daily-english-videos/terms.html`
   - **Privacy Policy URL**: `https://phongmanh.github.io/daily-english-videos/privacy.html`
   - Platform: **Web**, website `https://phongmanh.github.io/daily-english-videos/`
3. **Add products:**
   - **Login Kit** → Redirect URI: `https://phongmanh.github.io/daily-english-videos/tiktok-callback.html`
   - **Content Posting API** → leave **Direct Post off** (we only need Upload).
4. **Scopes:** `user.info.basic` and `video.upload`.
5. **Try it in Sandbox first** (no review needed): open the **Sandbox** tab → create a sandbox →
   add your TikTok account under **Target users**. Use the sandbox *Client key / secret* for steps 6–7.
6. **Submit for review** (top right). TikTok wants a short screen recording: show a video arriving in
   your TikTok inbox and you posting it. Review takes a few days to two weeks. After approval, run step 7
   again with the production keys.
7. On your computer:
   ```bash
   pip install requests cryptography
   python scripts/get_tiktok_token.py
   ```
   Log in with the Daily English account and allow access. Copy the code from the page into the script.
   It prints `TT_CLIENT_KEY`, `TT_REFRESH_TOKEN`, `TT_TOKEN_KEY` → add them, plus `TT_CLIENT_SECRET`, as secrets.

**Every day:** the drafts arrive when the videos are made (early morning). Post them at 12:00 / 18:00
(or whenever you like). Captions with a **Copy** button: <https://phongmanh.github.io/daily-english-videos/tiktok.html>.
TikTok allows at most **5 waiting drafts** in 24 hours: if you don't post or delete them, new ones are skipped.

## 3. Test

GitHub → **Actions → Daily video → Run workflow**
- Tick **dry run** first: it only makes the video. Download it from *Artifacts* and check it.
- Then run without dry run. YouTube gets a private video scheduled for 18:00 (Vietnam); Facebook gets a scheduled Reel (or a video post for the weekly long video).

## Daily schedule

- Two posts a day, made at night (GitHub may start runs late — that's OK; backups run if one is dropped):
  - **18:00** (made ~02:37): the cycle 5 word Shorts → 1 long video → repeat. The long video takes ~10–15 min to make.
  - **12:00** (made ~03:07): a review Short with 3 words already posted — "Do you remember?" and an A/B/C quiz on alternate days.
- To post a review by hand: **Run workflow** with kind = **review**.
- Posts are recorded in `state/published.json`; the next word comes from `words/queue.json`.

## If something breaks

- GitHub emails you when a run fails. Open the run to see which step failed.
- **Facebook token expired** → make a new one (step 2) and update `FB_PAGE_TOKEN`.
- **YouTube `invalid_grant`** → run `get_youtube_token.py` again and update `YT_REFRESH_TOKEN`.
- **Queue empty** → add words (see README).
- **To cancel a video before it goes public**: YouTube Studio → set it to private; Facebook → Meta Business Suite → Scheduled → delete.
