# Langkah 4-5: Reliabilitas pelabelan, label final, dan seluruh analisis
import json
import re
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score

from label_ai import L as LABEL_AI

ASPEK = ["Jam operasional", "Inovasi & adaptasi", "Budaya kerja & SDM", "Status BUMN & tata kelola", "Tarif",
         "Kecepatan & keandalan", "Pelayanan pelanggan", "Jangkauan jaringan", "Sistem & teknologi",
         "Layanan non-paket"]
KODE = dict(zip("JIBTRKPNSL", ASPEK))
SENT = ["Negatif", "Campuran", "Netral", "Positif"]
PELABEL = {"P1": "Ageng", "P2": "Kahfi", "P3": "AI"}

def baca(f):
    d = pd.read_excel(f, sheet_name="Pelabelan", dtype={"id_str": str}).sort_values("no").reset_index(drop=True)
    for c in ["sentimen"] + ASPEK + ["sebut_pesaing", "perlu_diskusi"]:
        d[c] = d[c].where(d[c].notna(), None)
        d[c] = d[c].map(lambda v: v.strip() if isinstance(v, str) else v)
    return d

p1, p2 = baca("label_p2.xlsx"), baca("label_kahfi.xlsx")
assert (p1.id_str == p2.id_str).all()
base = p1[["no", "id_str", "kode_akun", "jenis", "teks_asli"]].copy()

# Label AI ke format yang sama
rows = []
for no in base["no"]:
    s, kode, pes, dis, cat = LABEL_AI[no]
    r = {"no": no, "sentimen": s, "sebut_pesaing": "Ya" if pes else None, "perlu_diskusi": "Ya" if dis else None,
         "catatan": cat or None}
    for a in ASPEK:
        r[a] = None
    for tok in kode.split():
        r[KODE[tok[0]]] = "Puji" if tok[1] == "+" else "Kritik"
    rows.append(r)
p3 = pd.DataFrame(rows)
lab = {"P1": p1, "P2": p2, "P3": p3}

# ---------- 1. Reliabilitas ----------
def fleiss(mat):
    # mat: n_item x n_kategori (jumlah pelabel per kategori), jumlah pelabel sama per item
    n = mat.sum(axis=1)[0]
    p_j = mat.sum(axis=0) / mat.sum()
    P_i = (np.square(mat).sum(axis=1) - n) / (n * (n - 1))
    Pb, Pe = P_i.mean(), np.square(p_j).sum()
    return (Pb - Pe) / (1 - Pe)

rel = {}
s = pd.DataFrame({k: v["sentimen"] for k, v in lab.items()})
lengkap = s.dropna()
rel["n_sentimen_lengkap"] = len(lengkap)
rel["kosong_P2"] = int(s["P2"].isna().sum())
for a, b in combinations(lab, 2):
    m = s[[a, b]].dropna()
    rel[f"kappa_sentimen_{a}_{b}"] = round(cohen_kappa_score(m[a], m[b]), 3)
    rel[f"setuju_sentimen_{a}_{b}"] = round((m[a] == m[b]).mean(), 3)
mat = np.array([[sum(r == c for r in row) for c in SENT] for row in lengkap.values])
rel["fleiss_sentimen"] = round(fleiss(mat), 3)
# kesepakatan arah: Negatif vs bukan-Negatif
neg = (lengkap == "Negatif").astype(int)
ns = neg.sum(axis=1).values
rel["fleiss_negatif_vs_lain"] = round(fleiss(np.stack([ns, 3 - ns], 1)), 3)

asp_rel = []
for a in ASPEK:
    t = pd.DataFrame({k: v[a].fillna("—") for k, v in lab.items()})
    m3 = np.array([[sum(x == c for x in row) for c in ["Puji", "Kritik", "—"]] for row in t.values])
    pres = (t != "—").astype(int)
    asp_rel.append({"aspek": a,
                    "fleiss_label": round(fleiss(m3), 2),
                    "kappa_P1_P2": round(cohen_kappa_score(t.P1, t.P2), 2),
                    "disebut_P1": int(pres.P1.sum()), "disebut_P2": int(pres.P2.sum()), "disebut_P3": int(pres.P3.sum())})
asp_rel = pd.DataFrame(asp_rel)

# ---------- 2. Label final: suara mayoritas (2 dari 3) ----------
def mayoritas(vals, utama):
    hit = Counter(v for v in vals if v is not None)
    if not hit:
        return None, False
    top, n = hit.most_common(1)[0]
    if n >= 2:
        return top, False
    return utama, True            # seri -> ikut pelabel utama (P1), ditandai

final = base.copy()
seri_sent = 0
f_sent, f_seri = [], []
for i in range(len(base)):
    v, t = mayoritas([lab[k].at[i, "sentimen"] for k in lab], p1.at[i, "sentimen"])
    f_sent.append(v); f_seri.append(t)
final["sentimen_tiebreak_P1"] = f_sent
# Kasus seri (3 label berbeda) diputuskan dengan aturan codebook, dan dicatat alasannya
ADJUDIKASI = {
    6: ("Negatif", "Sarkasme: mengkritik jam buka 9-14; 'gercep' hanya untuk meterai"),
    9: ("Negatif", "Kritik jam tutup sore, disampaikan sebagai saran; tidak ada pujian"),
    11: ("Negatif", "Satire: Pos hanya ramai bila diwajibkan aturan"),
    17: ("Negatif", "Menjelaskan sebab kalah (telat gandeng marketplace, tutup akhir pekan); tidak ada pujian"),
    39: ("Netral", "Makna kalimat tidak jelas; tidak ada penilaian yang dapat dipastikan"),
    40: ("Negatif", "Sarkasme: Pos lebih dikenal untuk meterai daripada kirim barang"),
    50: ("Negatif", "Sarkasme; kalimat ini contoh resmi di codebook aturan 2"),
    54: ("Negatif", "Menyayangkan Pos tidak tertolong; nada kecewa (aturan 3)"),
    90: ("Campuran", "Kondisi Pos buruk ('in this economy') tetapi kolaborasi dinilai menolong"),
}
final["sentimen"] = f_sent
final["sentimen_seri"] = f_seri
final["alasan_adjudikasi"] = None
for no, (v, alasan) in ADJUDIKASI.items():
    i = final.index[final["no"] == no][0]
    assert final.at[i, "sentimen_seri"], no
    final.at[i, "sentimen"] = v
    final.at[i, "alasan_adjudikasi"] = alasan
assert final.loc[final.sentimen_seri, "alasan_adjudikasi"].notna().all()
for a in ASPEK:
    out = []
    for i in range(len(base)):
        vals = [lab[k].at[i, a] or "—" for k in lab]
        hit = Counter(vals).most_common(1)[0]
        out.append(None if (hit[0] == "—" and hit[1] >= 2) else (hit[0] if hit[1] >= 2 else (p1.at[i, a])))
    final[a] = out
final["sebut_pesaing"] = [sum(lab[k].at[i, "sebut_pesaing"] == "Ya" for k in lab) >= 2 for i in range(len(base))]
for k, nm in PELABEL.items():
    final[f"sentimen_{nm}"] = lab[k]["sentimen"]

# gabung metadata engagement & waktu
meta = pd.read_csv("data_bersih_pos.csv", dtype={"id_str": str})
final = final.merge(meta[["id_str", "username", "waktu_wib", "favorite_count", "retweet_count", "reply_count",
                          "quote_count", "teks_bersih", "tweet_url"]], on="id_str")
final["waktu_wib"] = pd.to_datetime(final["waktu_wib"])

# ---------- 3. Deskriptif ----------
N = len(final)
desk = {"N": N, "reply": int((final.jenis == "reply").sum()), "quote": int((final.jenis == "quote").sum()),
        "akun_unik": int(final.username.nunique()),
        "mulai": str(final.waktu_wib.min()), "akhir": str(final.waktu_wib.max()),
        "like_total": int(final.favorite_count.sum()), "like_median": float(final.favorite_count.median()),
        "like_nol_pct": round((final.favorite_count == 0).mean() * 100, 1),
        "rt_total": int(final.retweet_count.sum()),
        "share_like_top1": round(final.favorite_count.max() / final.favorite_count.sum() * 100, 1),
        "kata_median": float(final.teks_bersih.str.split().str.len().median())}
t0 = pd.Timestamp("2026-11-22 10:00", tz="Asia/Jakarta")
final["blok_jam"] = ((final.waktu_wib - t0).dt.total_seconds() // (3 * 3600)).astype(int)
per_blok = final.groupby("blok_jam").size().reindex(range(0, 9), fill_value=0)
waktu = [{"mulai": (t0 + pd.Timedelta(hours=3 * b)).strftime("%d/%m %H.%M"), "jumlah": int(n)} for b, n in per_blok.items()]

# ---------- 4. Sentimen ----------
def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)

sent = []
for lab_ in SENT:
    k = int((final.sentimen == lab_).sum())
    lo, hi = wilson(k, N)
    sent.append({"sentimen": lab_, "n": k, "pct": round(k / N * 100, 1), "lo": round(lo * 100, 1), "hi": round(hi * 100, 1)})
ct = pd.crosstab(final.jenis, final.sentimen).reindex(columns=SENT, fill_value=0)
chi_jenis = stats.chi2_contingency(ct)
ct2 = pd.crosstab(final.jenis, final.sentimen == "Negatif")
fisher_jenis = stats.fisher_exact(ct2.values)

# ---------- 5. Aspek ----------
asp = []
for a in ASPEK:
    k = int((final[a] == "Kritik").sum()); p = int((final[a] == "Puji").sum())
    asp.append({"aspek": a, "kritik": k, "puji": p, "total": k + p,
                "pct_opini": round((k + p) / N * 100, 1),
                "rasio_kritik": round(k / (k + p) * 100, 0) if k + p else None})
asp = pd.DataFrame(asp).sort_values("total", ascending=False)
# Uji binomial per aspek: apakah kritik > puji secara signifikan
asp["p_binom"] = [round(stats.binomtest(r.kritik, r.total, 0.5).pvalue, 4) if r.total else None for r in asp.itertuples()]
final["jumlah_aspek"] = final[ASPEK].notna().sum(axis=1)
# Uji kesamaan frekuensi aspek (goodness-of-fit) untuk aspek yang dikritik
gof = stats.chisquare(asp["kritik"].values)
# Ko-okurensi aspek
co = Counter()
for _, r in final.iterrows():
    hadir = [a for a in ASPEK if pd.notna(r[a])]
    for x, y in combinations(sorted(hadir), 2):
        co[(x, y)] += 1
co_top = [{"pasangan": f"{x} + {y}", "n": n} for (x, y), n in co.most_common(6)]

# ---------- 6. Kata kunci ----------
STOP = set("""yang dan di ke dari ini itu saja aja juga sudah tidak ada untuk dengan pada adalah karena kalau tapi
jadi bisa mau pas lagi masih cuma baru udah saya kamu dia mereka kita kami ya sih kok lho deh dong nih tuh kan
mas mbak bang kang pak lebih paling banget sama dulu sekarang soal buat kayak seperti apa siapa kenapa gimana
yg the of in and to a is on for this it by kali juga pun malah emang memang punya satu dua tiga hal ga gak
nya an lah kah pernah terakhir pakai pake kirim pos indonesia kantor jam jasa hari tiap mana makin lu gw ini
padahal begitu banyak orang semua sih nah wah eh oh jg tp pd dg dgn kalo klo kl sampai sampe sendiri tetap
harus kadang biasanya waktu atau sebagai segala aspek bener benar ok oke kali kok jangan harap dalam secara
bahkan apalagi masalahnya ya allah tau tahu hanya dah kek gue gua aku ku diri jadii lain ama sudah bukan""".split())
def token(t):
    return [w for w in t.split() if len(w) > 2 and w not in STOP and not w.isdigit()]
final["teks_bersih"] = final.teks_bersih.fillna("").str.replace("materai", "meterai")
tok_all = final.teks_bersih.map(token)
uni = Counter(w for ts in tok_all for w in set(ts))
bi = Counter()
FUNGSI = STOP | {"salah", "satu", "indo", "lewat", "berurusan"}
for t in final.teks_bersih.fillna(""):
    ws = [w for w in t.split() if w not in FUNGSI and not w.isdigit() and len(w) > 2]
    for x, y in set(zip(ws, ws[1:])):
        bi[f"{x} {y}"] += 1
top_uni = uni.most_common(20)
top_bi = [(b, n) for b, n in bi.most_common(60) if n >= 2][:15]

# ---------- 7. Pesaing ----------
PESAING = {"SPX / Shopee Express": r"\bspx\b|shopee express", "J&T": r"\bj&t\b|\bjnt\b", "JNE": r"\bjne\b",
           "SiCepat": r"si ?cepat", "GoSend": r"gosend", "Wahana": r"wahana", "Paxel": r"paxel",
           "FedEx / DHL": r"fedex|\bdhl\b", "Indomaret / Alfamart / m-banking": r"indo ?alfa|mobile banking|indomaret|alfamart",
           "'Swasta' (umum)": r"\bswasta"}
txt = final.teks_asli.str.lower()
pes = []
for nama, pat in PESAING.items():
    m = txt.str.contains(pat, regex=True)
    sub = final[m]
    pes.append({"pesaing": nama, "n": int(m.sum()),
                "aspek": ", ".join(f"{a} ({c})" for a, c in Counter(a for _, r in sub.iterrows() for a in ASPEK if pd.notna(r[a])).most_common(2))})
pes = pd.DataFrame(pes).sort_values("n", ascending=False)
final["sebut_pesaing_teks"] = txt.str.contains("|".join(PESAING.values()), regex=True)

# ---------- 8. Uji tambahan: engagement ----------
neg_l = final.loc[final.sentimen == "Negatif", "favorite_count"]
lain_l = final.loc[final.sentimen != "Negatif", "favorite_count"]
mw = stats.mannwhitneyu(neg_l, lain_l, alternative="greater")
mw_tanpa = stats.mannwhitneyu(neg_l[neg_l < neg_l.max()], lain_l, alternative="greater")
eng = {"median_neg": float(neg_l.median()), "median_lain": float(lain_l.median()),
       "mean_neg": round(neg_l.mean(), 1), "mean_lain": round(lain_l.mean(), 1),
       "pct_dapat_like_neg": round((neg_l > 0).mean() * 100, 1), "pct_dapat_like_lain": round((lain_l > 0).mean() * 100, 1),
       "U": float(mw.statistic), "p": round(mw.pvalue, 4), "p_tanpa_outlier": round(mw_tanpa.pvalue, 4),
       "n_neg": len(neg_l), "n_lain": len(lain_l)}
# Spearman: jumlah aspek vs like
sp = stats.spearmanr(final.jumlah_aspek, final.favorite_count)
eng["spearman_aspek_like"] = (round(sp.statistic, 3), round(sp.pvalue, 3))
top_eng = final.nlargest(5, "favorite_count")[["kode_akun", "jenis", "sentimen", "favorite_count", "retweet_count", "teks_asli"]]

# ---------- Simpan ----------
hasil = {"rel": rel, "desk": desk, "waktu": waktu, "sent": sent,
         "ct_jenis": ct.to_dict(), "chi_jenis": [round(chi_jenis.statistic, 3), round(chi_jenis.pvalue, 4), int(chi_jenis.dof)],
         "fisher_jenis": [round(fisher_jenis.statistic, 3), round(fisher_jenis.pvalue, 4)], "ct2": ct2.values.tolist(),
         "seri_sentimen": int(sum(f_seri)), "neg_tiebreak_P1": int((final.sentimen_tiebreak_P1 == "Negatif").sum()), "gof_kritik": [round(gof.statistic, 2), float(gof.pvalue)],
         "co_top": co_top, "top_uni": top_uni, "top_bi": top_bi, "eng": eng,
         "multi_aspek": int((final.jumlah_aspek >= 2).sum()), "tanpa_aspek": int((final.jumlah_aspek == 0).sum()),
         "pesaing_teks": int(final.sebut_pesaing_teks.sum())}
json.dump(hasil, open("analisis/hasil.json", "w"), indent=1, default=str, ensure_ascii=False)
asp.to_csv("analisis/aspek.csv", index=False)
asp_rel.to_csv("analisis/reliabilitas_aspek.csv", index=False)
pes.to_csv("analisis/pesaing.csv", index=False)
final.to_pickle("analisis/final.pkl")
for kk, vv in lab.items():
    vv.to_pickle(f"analisis/lab_{kk}.pkl")

print(json.dumps({k: hasil[k] for k in ["rel", "desk", "sent", "chi_jenis", "fisher_jenis", "ct2", "seri_sentimen", "gof_kritik", "eng", "multi_aspek", "tanpa_aspek", "pesaing_teks"]}, indent=1, default=str, ensure_ascii=False))
print(ct)
print(asp.to_string()); print(asp_rel.to_string()); print(pes.to_string())
print(co_top); print(top_uni); print(top_bi); print(waktu)
print(top_eng.to_string())
