import os, tempfile, subprocess, shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import imageio_ffmpeg

app = FastAPI(title="AI TikTok Editor")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#0b0d12"><title>AI TikTok Editor</title>
<style>
:root{--bg:#0b0d12;--p:#151a24;--line:#2b3445;--txt:#f5f6fa;--muted:#9aa5b5;--a:#8b5cf6}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 90% 0,#282044,transparent 35%),var(--bg);color:var(--txt);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{padding:20px;border-bottom:1px solid var(--line);font-weight:850;font-size:20px}header span{color:#b99aff}main{max-width:720px;margin:auto;padding:18px 14px 45px}h1{font-size:27px;margin:8px 0}p{color:var(--muted)}.card{background:var(--p);border:1px solid var(--line);border-radius:17px;padding:16px;margin:14px 0}h2{font-size:16px;margin:0 0 12px}
.upload{border:1.5px dashed #66548b;background:#1b1828;border-radius:13px;text-align:center;padding:20px}input[type=file]{width:100%;color:#cbd2df}label{display:block;font-size:13px;margin:12px 0 6px;color:#cbd2df}input[type=number],input[type=text],select{width:100%;background:#0c1017;border:1px solid var(--line);border-radius:10px;padding:11px;color:white;font:inherit}button{border:0;border-radius:12px;background:linear-gradient(110deg,#7854e8,#a34edb);color:white;padding:13px 17px;font-weight:800;font-size:14px;width:100%;margin-top:14px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.muted{font-size:12px;color:var(--muted)}#status{margin-top:12px;color:#71e2d6;font-size:13px;white-space:pre-wrap}.bar{height:7px;background:#30394a;border-radius:9px;overflow:hidden;margin-top:10px;display:none}.bar div{height:100%;width:0;background:#9b7aff}a{color:#c5aaff}.warning{font-size:12px;background:#292311;border-left:3px solid #e7b94c;padding:10px;border-radius:7px;color:#f4dfaa}
</style></head><body><header>✦ AI <span>TikTok Editor</span></header><main>
<h1>Ton studio de montage</h1><p>Importe une vidéo, choisis le format et lance un premier traitement automatique.</p>
<section class="card"><h2>01 · Ta vidéo</h2><div class="upload"><input id="file" type="file" accept="video/*"><div class="muted" id="fileinfo">Sélectionne une vidéo depuis ton iPhone.</div></div>
<div class="row"><div><label>Format de sortie</label><select id="ratio"><option value="9:16">TikTok · 9:16</option><option value="1:1">Carré · 1:1</option><option value="16:9">Paysage · 16:9</option></select></div><div><label>Qualité</label><select id="quality"><option value="1080">1080p</option><option value="720">720p</option></select></div></div>
<div class="row"><div><label>Début (secondes)</label><input id="start" type="number" min="0" step="0.1" value="0"></div><div><label>Fin (secondes, facultatif)</label><input id="end" type="number" min="0" step="0.1" placeholder="Jusqu'à la fin"></div></div>
<label>Texte à afficher à l'écran (facultatif)</label><input id="caption" type="text" maxlength="120" placeholder="Ex. REGARDE JUSQU'À LA FIN !">
<div class="warning">Version initiale : recadrage, découpe et texte fixe. Les sous-titres automatiques synchronisés, effets avancés et l'assistant Claude seront ajoutés ensuite. Ne téléverse pas de vidéo privée ou sensible.</div>
<button id="go">Lancer le montage</button><div class="bar" id="bar"><div id="progress"></div></div><div id="status"></div></section>
<section class="card"><h2>02 · Comment ça marche ?</h2><p class="muted">Le serveur reçoit ta vidéo, FFmpeg la traite puis ton iPhone télécharge le MP4 final. Sur l'offre gratuite, le premier lancement peut prendre un peu de temps et les gros fichiers peuvent échouer.</p></section>
</main><script>
const $=id=>document.getElementById(id);let busy=false;
$('file').addEventListener('change',()=>{$('fileinfo').textContent=$('file').files[0] ? $('file').files[0].name+' · '+($('file').files[0].size/1048576).toFixed(1)+' Mo' : 'Aucun fichier';});
$('go').addEventListener('click',async()=>{
 if(busy)return;const f=$('file').files[0];if(!f){$('status').textContent='Choisis d’abord une vidéo.';return;}
 busy=true;$('go').disabled=true;$('go').textContent='Traitement en cours…';$('status').textContent='Envoi et traitement en cours. Garde cette page ouverte.';$('bar').style.display='block';$('progress').style.width='25%';
 const data=new FormData();data.append('video',f);data.append('ratio',$('ratio').value);data.append('quality',$('quality').value);data.append('trim_start',$('start').value||'0');data.append('trim_end',$('end').value||'');data.append('caption',$('caption').value);
 try{const r=await fetch('/process',{method:'POST',body:data});if(!r.ok){let msg=await r.text();throw new Error(msg.slice(0,500));}
 $('progress').style.width='85%';const blob=await r.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='ai-tiktok-editor.mp4';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);$('progress').style.width='100%';$('status').textContent='Terminé ! Le MP4 a été téléchargé. Vérifie l’app Fichiers ou le dossier Téléchargements.';
 }catch(e){$('status').textContent='Erreur : '+e.message+'\\nSi le serveur vient de se réveiller, réessaie dans une minute.';$('progress').style.width='0%';}
 finally{busy=false;$('go').disabled=false;$('go').textContent='Lancer le montage';}
});
</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.get("/health")
def health():
    return {"status": "ok", "engine": "FFmpeg"}

@app.post("/process")
async def process_video(
    video: UploadFile = File(...),
    ratio: str = Form("9:16"),
    quality: str = Form("1080"),
    trim_start: float = Form(0),
    trim_end: str = Form(""),
    caption: str = Form("")
):
    if not video.filename:
        raise HTTPException(400, "Fichier vidéo manquant.")
    if ratio not in ("9:16", "1:1", "16:9"):
        raise HTTPException(400, "Format non pris en charge.")
    if quality not in ("720", "1080"):
        raise HTTPException(400, "Qualité non prise en charge.")
    try:
        start = max(0.0, float(trim_start))
        end = float(trim_end) if trim_end.strip() else None
    except ValueError:
        raise HTTPException(400, "Durée de découpe invalide.")
    if end is not None and end <= start:
        raise HTTPException(400, "La fin doit être supérieure au début.")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "input_video"
        out = Path(td) / "edited.mp4"
        size = 0
        try:
            with src.open("wb") as f:
                while True:
                    chunk = await video.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 180 * 1024 * 1024:
                        raise HTTPException(413, "Vidéo trop volumineuse (limite prototype : 180 Mo).")
                    f.write(chunk)
        finally:
            await video.close()

        if size == 0:
            raise HTTPException(400, "Fichier vide.")
        if ratio == "9:16":
            w, h = (720, 1280) if quality == "720" else (1080, 1920)
        elif ratio == "1:1":
            w = h = 720 if quality == "720" else 1080
        else:
            w, h = (1280, 720) if quality == "720" else (1920, 1080)

        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
        if caption.strip():
            safe = caption.strip().replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%").replace(",", "\\,").replace("[", "\\[").replace("]", "\\]")
            vf += f",drawtext=text='{safe}':fontcolor=white:fontsize={max(28, w//22)}:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.78"
        cmd = [ffmpeg, "-y", "-i", str(src)]
        if start > 0:
            cmd += ["-ss", str(start)]
        if end is not None:
            cmd += ["-t", str(end - start)]
        cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0 or not out.exists():
            detail = (result.stderr or "Erreur FFmpeg")[-1600:]
            raise HTTPException(500, "Le traitement vidéo a échoué : " + detail)
        return FileResponse(out, media_type="video/mp4", filename="ai-tiktok-editor.mp4")
