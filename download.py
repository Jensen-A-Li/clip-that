from db import ROOT
import yt_dlp

RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def get_clips_to_download(conn, limit=5):
    get_clips_from_db_sql= """
        SELECT id, url from clips
        WHERE status = 'new'
        ORDER BY view_count DESC
        LIMIT ? 
    """

    clips = conn.execute(get_clips_from_db_sql, (limit,)).fetchall()
    return clips

def download_clip(url, clip_id):
    opts = {
        "outtmpl": str(RAW_DIR / f"{clip_id}.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "quiet": True, 
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

def mark_clip(conn, clip_id, status, file_path=None):
    update_clip_status_sql = """
        UPDATE clips SET status = ?, file_path = ?
        WHERE id = ?
    """

    conn.execute(update_clip_status_sql, (status, file_path, clip_id))
    conn.commit()

def download_clips(conn):
    # lookup clips in db and download them
        clips_to_dl = get_clips_to_download(conn, limit=1)
    
        for clip_id, url in clips_to_dl:
            try:
                file_path = download_clip(url, clip_id)
                mark_clip(conn, clip_id, "downloaded", file_path)
            except yt_dlp.utils.DownloadError as err:
                print(f"Failed to download {clip_id}: {err}")
                mark_clip(conn, clip_id, "failed")