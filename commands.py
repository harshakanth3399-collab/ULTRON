import subprocess
import webbrowser
import urllib.parse
import yt_dlp


# -----------------------------
# Open YouTube Video
# -----------------------------
def play_youtube(search):

    ydl_opts = {
        "quiet": True,
        "default_search": "ytsearch10"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(search, download=False)
            videos = info["entries"]

            best_video = None
            best_score = -1

            for video in videos:

                score = 0

                title = video.get("title", "").lower()
                uploader = video.get("uploader", "").lower()

                for word in search.lower().split():
                    if word in title:
                        score += 5

                if "official" in title:
                    score += 10

                if "trailer" in title:
                    score += 10

                if "official" in uploader:
                    score += 5

                if "t-series" in uploader:
                    score += 5

                if score > best_score:
                    best_score = score
                    best_video = video

            if best_video:
                print("▶ Playing:", best_video["title"])
                webbrowser.open(best_video["webpage_url"])
            else:
                webbrowser.open("https://youtube.com")

    except Exception as e:
        print("YouTube Error:", e)


# -----------------------------
# Google Search
# -----------------------------
def google_search(command):

    search = command

    for word in [
        "search",
        "google",
        "for",
        "open"
    ]:
        search = search.replace(word, "")

    search = search.strip()

    if search:
        url = "https://www.google.com/search?q=" + urllib.parse.quote(search)
    else:
        url = "https://google.com"

    webbrowser.open(url)


# -----------------------------
# Execute Commands
# -----------------------------
def execute(command):

    command = command.lower().strip()

    # Exit
    if "exit ultron" in command:
        return False

    # Notepad
    if "notepad" in command:
        subprocess.Popen("notepad.exe")
        return True

    # Calculator
    if "calculator" in command:
        subprocess.Popen("calc.exe")
        return True

    # Chrome
    if "chrome" in command:
        subprocess.Popen(
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        )
        return True

    # Google
    if "google" in command:
        google_search(command)
        return True

    # YouTube
    if "youtube" in command:

        search = command

        for word in [
            "play",
            "youtube",
            "on",
            "open",
            "and"
        ]:
            search = search.replace(word, "")

        search = search.strip()

        if search:
            play_youtube(search)
        else:
            webbrowser.open("https://youtube.com")

        return True

    # Unknown Command
    return None