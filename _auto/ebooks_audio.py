#!/usr/bin/env python3
"""
EbookClassics — livres audio MP3, suite (v2).
- Liste des enregistrements LibriVox préparée à l'avance (audio_plan.json) : titres sans article
  (« Great Gatsby »), édition par édition, langue et durée vérifiées.
- Chaque MP3 est envoyé sur Cloudflare R2 avec l'en-tête de téléchargement (le bouton MP3 enregistre le fichier).
- Les 50 MP3 déjà en ligne reçoivent aussi cet en-tête (copie sur place, sans nouvel envoi).
- audio.json est publié sur GitHub après chaque livre : le site se met à jour au fur et à mesure,
  et la commande peut être relancée à tout moment sans refaire ce qui est fait.
"""
import datetime, hashlib, hmac, http.client, json, os, subprocess, sys, time, urllib.parse, urllib.request

REPO = os.path.expanduser("~/ebookclassics-files")
WORK = os.path.expanduser("~/ebookclassics-audio")
CONF = os.path.expanduser("~/r2.conf")
PLAN = os.path.expanduser("~/audio_plan.json")
UA = {"User-Agent": "EbookClassicsBot/1.1 (https://github.com/medamineamzil-design/ebookclassics-files)"}
EMPTY = hashlib.sha256(b"").hexdigest()

def get(url, tries=5, timeout=300):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(10 * (i + 1))

def strip_tags(data):
    if data[:3] == b"ID3":
        size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
        data = data[10 + size:]
    if len(data) > 128 and data[-128:-125] == b"TAG":
        data = data[:-128]
    return data

def id3(title, artist):
    def frame(fid, text):
        payload = b"\x03" + text.encode("utf-8")
        return fid.encode() + len(payload).to_bytes(4, "big") + b"\x00\x00" + payload
    body = frame("TIT2", title) + frame("TPE1", artist) + frame("TALB", title) + frame("TPUB", "EbookClassics")
    n = len(body)
    return b"ID3\x04\x00\x00" + bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F]) + body

def build_mp3(p, out_path):
    tmp = out_path + ".part"
    with open(tmp, "wb") as out:
        out.write(id3(p["title"], p["author"]))
        n = len(p["sections"])
        for i, url in enumerate(p["sections"], 1):
            print(f"      partie {i}/{n}", flush=True)
            out.write(strip_tags(get(url.replace("http://", "https://"))))
            time.sleep(0.3)
    os.replace(tmp, out_path)

def read_conf():
    c = {}
    for line in open(CONF, encoding="utf-8"):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1); c[k.strip()] = v.strip()
    return c

def r2_request(conf, key, extra, body_path=None):
    host = f"{conf['account_id']}.r2.cloudflarestorage.com"
    uri = "/" + conf["bucket"] + "/" + urllib.parse.quote(key)
    now = datetime.datetime.utcnow()
    amzdate, datestamp = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    size = os.path.getsize(body_path) if body_path else 0
    payload = "UNSIGNED-PAYLOAD" if body_path else EMPTY
    headers = {"host": host, "x-amz-content-sha256": payload, "x-amz-date": amzdate, "content-length": str(size)}
    headers.update({k.lower(): v for k, v in extra.items()})
    signed = ";".join(sorted(headers))
    canon = "\n".join(["PUT", uri, "", "".join(f"{k}:{headers[k]}\n" for k in sorted(headers)), signed, payload])
    scope = f"{datestamp}/auto/s3/aws4_request"
    sts = "\n".join(["AWS4-HMAC-SHA256", amzdate, scope, hashlib.sha256(canon.encode()).hexdigest()])
    k = ("AWS4" + conf["secret_access_key"]).encode()
    for part in (datestamp, "auto", "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    headers["authorization"] = (f"AWS4-HMAC-SHA256 Credential={conf['access_key_id']}/{scope}, "
                                f"SignedHeaders={signed}, Signature={sig}")
    conn = http.client.HTTPSConnection(host, timeout=900)
    conn.putrequest("PUT", uri, skip_host=True, skip_accept_encoding=True)
    for h, v in headers.items():
        conn.putheader(h, v)
    conn.endheaders()
    if body_path:
        with open(body_path, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                conn.send(chunk)
    r = conn.getresponse(); body = r.read()
    if r.status not in (200, 201):
        raise RuntimeError(f"R2 a refusé ({r.status}) : {body[:200]!r}")
    return conf["public_url"].rstrip("/") + "/" + urllib.parse.quote(key)

def dispo(key):
    return f'attachment; filename="{os.path.basename(key)}"'

def publish(msg):
    g = ["git", "-C", REPO]
    subprocess.run(g + ["add", "audio.json", "_rapports/audio-a-synthetiser.txt"], capture_output=True)
    if subprocess.run(g + ["commit", "-q", "-m", msg], capture_output=True).returncode:
        return
    for _ in range(3):
        if subprocess.run(g + ["push", "-q"], capture_output=True).returncode == 0:
            return
        subprocess.run(g + ["pull", "-q", "--rebase", "--autostash"], capture_output=True)
    print("   ! audio.json pas encore publié sur GitHub (nouvel essai au prochain livre)", flush=True)

def main():
    conf = read_conf()
    if not all(conf.get(k) and "..." not in conf[k] for k in ("account_id", "access_key_id", "secret_access_key", "bucket", "public_url")):
        print("!! ~/r2.conf incomplet : arrêt."); return
    os.makedirs(WORK, exist_ok=True)
    plan = json.load(open(PLAN))
    apath = os.path.join(REPO, "audio.json")
    audio = json.load(open(apath)) if os.path.exists(apath) else {}
    def save():
        json.dump(audio, open(apath, "w"), indent=1, sort_keys=True)

    # 1. en-tête de téléchargement sur les MP3 déjà en ligne
    base = conf["public_url"].rstrip("/") + "/"
    fixed = 0
    for slug, eds in sorted(audio.items()):
        for lang, e in eds.items():
            if e.get("dl") or not e.get("url", "").startswith(base):
                continue
            key = urllib.parse.unquote(e["url"][len(base):])
            try:
                r2_request(conf, key, {"x-amz-copy-source": "/" + conf["bucket"] + "/" + urllib.parse.quote(key),
                                        "x-amz-metadata-directive": "REPLACE", "content-type": "audio/mpeg",
                                        "content-disposition": dispo(key)})
                e["dl"] = True; fixed += 1
            except Exception as ex:
                print(f"   ! {slug} [{lang}] : en-tête non modifié ({ex})", flush=True)
    if fixed:
        save(); publish(f"Livres audio : bouton MP3 = telechargement ({fixed} fichiers)")
        print(f"== {fixed} MP3 déjà en ligne : téléchargement direct activé ==", flush=True)

    # 2. nouveaux livres audio
    with open(os.path.join(REPO, "_rapports", "audio-a-synthetiser.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(plan["missing"]) + "\n")
    todo = [p for p in plan["picks"] if not audio.get(p["slug"], {}).get(p["lang"])]
    print(f"== {len(todo)} livres audio à ajouter ==", flush=True)
    for n, p in enumerate(todo, 1):
        slug, lang = p["slug"], p["lang"]
        stem = slug if lang == "en" else f"{slug}-{lang}"
        key = f"audio/{slug}/{stem}.mp3"
        mp3 = os.path.join(WORK, stem + ".mp3")
        h = p["secs"] // 3600
        print(f"[{n}/{len(todo)}] {p['title']} [{lang}] — LibriVox « {p['lv_title']} » ({h} h {p['secs'] % 3600 // 60:02d})", flush=True)
        try:
            if not os.path.exists(mp3):
                build_mp3(p, mp3)
            size = os.path.getsize(mp3)
            url = r2_request(conf, key, {"content-type": "audio/mpeg", "content-disposition": dispo(key)}, mp3)
            os.remove(mp3)
            audio.setdefault(slug, {})[lang] = {"source": "librivox", "duration": p["secs"], "bytes": size, "url": url, "dl": True}
            save(); publish(f"Livre audio : {p['title']} [{lang}]")
            print(f"   ✓ en ligne ({size // 1048576} Mo)", flush=True)
        except Exception as ex:
            print(f"   ! erreur : {ex} (sera repris à la prochaine relance)", flush=True)
    save(); publish("Livres audio : liste des MP3 en ligne")
    total = sum(len(v) for v in audio.values())
    print(f"\nMP3 en ligne : {total} | sans enregistrement LibriVox : {len(plan['missing'])}")

if __name__ == "__main__":
    main()
