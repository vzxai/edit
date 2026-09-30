// Streaming scanner for the YFCC100M SQLite dump (page size 1024, schema format 1).
// Reads raw pages from stdin, emits one TSV line per *video* row.
// Videos are detected from the record header alone: a video's downloadurl is
//   http://www.flickr.com/videos/<uid>/<photoid>/play/orig/<secret10>
// whose length is 51 + len(uid) + digits(photoid); photo URLs are much shorter.
// Overflow chains are resolved from a ring buffer of recent pages or from pages
// that stream by later; anything unresolvable is emitted as "#UNRES" for a fix-up pass.
// Usage: curl -r a-b URL | scan <first_page_number>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define PS 1024
#define U 1024
#define NCOL 23
#define RING 32768          /* 32 MB of recent pages */
#define HT 65536            /* pending hash table slots */

static int varint(const uint8_t *b, int i, int lim, uint64_t *out) {
    uint64_t v = 0;
    for (int k = 0; k < 9; k++) {
        if (i + k >= lim) return -1;
        uint8_t c = b[i + k];
        if (k == 8) { *out = (v << 8) | c; return i + 9; }
        v = (v << 7) | (c & 0x7f);
        if (c < 0x80) { *out = v; return i + k + 1; }
    }
    return -1;
}
static uint32_t be32(const uint8_t *b) { return ((uint32_t)b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]; }
static int ndig(uint64_t v) { int n = 1; while (v >= 10) { v /= 10; n++; } return n; }

typedef struct { uint64_t rowid, P; uint32_t next; int have; uint8_t *buf; int used; } Pend;
static Pend *pend[HT];
static uint32_t pend_key[HT];

static uint8_t ring[RING][PS];
static uint64_t ring_pg[RING];

static void emit(uint64_t rowid, const uint8_t *rec, int len) {
    uint64_t hs; int j = varint(rec, 0, len, &hs);
    if (j < 0 || hs > (uint64_t)len) return;
    uint64_t types[NCOL + 2]; int nt = 0;
    while ((uint64_t)j < hs && nt < NCOL + 1) { j = varint(rec, j, (int)hs, &types[nt]); if (j < 0) return; nt++; }
    if (nt != NCOL) return;
    printf("%llu", (unsigned long long)rowid);
    uint64_t k = hs;
    for (int col = 1; col < NCOL; col++) {
        uint64_t t = types[col], l = 0;
        putchar('\t');
        if (t >= 13 && (t & 1)) l = (t - 13) / 2;
        else if (t >= 12) l = (t - 12) / 2;
        else if (t >= 1 && t <= 6) { static const int sz[] = {0,1,2,3,4,6,8}; l = sz[t]; }
        else if (t == 7) l = 8;
        if (k + l > (uint64_t)len) { fputs("\\TRUNC", stdout); k += l; continue; }
        if (t >= 13 && (t & 1)) {
            for (uint64_t q = 0; q < l; q++) { uint8_t c = rec[k + q]; if (c == '\t' || c == '\n' || c == '\r') c = ' '; putchar(c); }
        } else if (t >= 1 && t <= 6) {
            int64_t v = (rec[k] & 0x80) ? -1 : 0;
            for (uint64_t q = 0; q < l; q++) v = (v << 8) | rec[k + q];
            printf("%lld", (long long)v);
        } else if (t == 8) putchar('0');
        else if (t == 9) putchar('1');
        k += l;
    }
    putchar('\n');
}

static void emit_unres(Pend *e) {
    printf("#UNRES\t%llu\t%llu\t%u\t%d\t", (unsigned long long)e->rowid, (unsigned long long)e->P, e->next, e->used);
    for (int i = 0; i < e->used; i++) printf("%02x", e->buf[i]);
    putchar('\n');
}

static void ht_put(Pend *e) {
    uint32_t h = (e->next * 2654435761u) % HT;
    for (int n = 0; n < HT; n++, h = (h + 1) % HT) if (!pend[h]) { pend[h] = e; pend_key[h] = e->next; return; }
    emit_unres(e); free(e->buf); free(e);   /* table full */
}
static Pend *ht_take(uint32_t pg) {
    uint32_t h = (pg * 2654435761u) % HT;
    for (int n = 0; n < HT; n++, h = (h + 1) % HT) {
        if (!pend[h]) return NULL;
        if (pend_key[h] == pg) {
            Pend *e = pend[h]; pend[h] = NULL;
            /* re-insert the rest of the probe cluster so lookups keep working */
            uint32_t k = (h + 1) % HT;
            while (pend[k]) { Pend *x = pend[k]; pend[k] = NULL; ht_put(x); k = (k + 1) % HT; }
            return e;
        }
    }
    return NULL;
}

/* feed overflow page content into a pending record; returns 1 if complete */
static int feed(Pend *e, const uint8_t *pg) {
    int want = (int)e->P - e->used; if (want > U - 4) want = U - 4;
    memcpy(e->buf + e->used, pg + 4, want); e->used += want;
    e->next = be32(pg);
    return (uint64_t)e->used >= e->P || e->next == 0;
}

static uint64_t cur_pg, first_pg;

static void advance(Pend *e) {
    /* follow the chain through pages already in the ring buffer */
    for (;;) {
        if ((uint64_t)e->used >= e->P || e->next == 0) { emit(e->rowid, e->buf, e->used); free(e->buf); free(e); return; }
        uint64_t nx = e->next;
        if (nx > cur_pg) { ht_put(e); return; }
        if (nx < first_pg || ring_pg[nx % RING] != nx) { emit_unres(e); free(e->buf); free(e); return; }
        if (feed(e, ring[nx % RING])) { emit(e->rowid, e->buf, e->used); free(e->buf); free(e); return; }
    }
}

int main(int argc, char **argv) {
    first_pg = cur_pg = argc > 1 ? strtoull(argv[1], 0, 10) : 1;
    uint64_t pages = 0, videos = 0;
    for (;;) {
        uint8_t *p = ring[cur_pg % RING];
        if (fread(p, 1, PS, stdin) != PS) break;
        ring_pg[cur_pg % RING] = cur_pg;
        /* a pending chain waiting for this page? */
        Pend *w;
        while ((w = ht_take((uint32_t)cur_pg))) {
            if (feed(w, p)) { emit(w->rowid, w->buf, w->used); free(w->buf); free(w); }
            else advance(w);
        }
        int off = (cur_pg == 1) ? 100 : 0;
        if (p[off] == 0x0D) {
            int n = (p[off + 3] << 8) | p[off + 4];
            for (int ci = 0; ci < n; ci++) {
                int cp = off + 8 + 2 * ci;
                if (cp + 1 >= PS) break;
                int c = (p[cp] << 8) | p[cp + 1];
                if (c < 8 || c >= PS) continue;
                uint64_t P, rowid;
                int i = varint(p, c, PS, &P); if (i < 0) continue;
                i = varint(p, i, PS, &rowid); if (i < 0) continue;
                int X = U - 35, M = ((U - 12) * 32) / 255 - 23, L;
                uint32_t ov = 0;
                if (P <= (uint64_t)X) L = (int)P;
                else {
                    int K = M + (int)((P - M) % (U - 4));
                    L = (K <= X) ? K : M;
                    if (i + L + 4 > PS) continue;
                    ov = be32(p + i + L);
                }
                if (i + L > PS) continue;
                const uint8_t *rec = p + i;
                uint64_t hs; int j = varint(rec, 0, L, &hs);
                if (j < 0 || hs > (uint64_t)L) continue;
                uint64_t types[NCOL + 2]; int nt = 0;
                while ((uint64_t)j < hs && nt < NCOL + 1) { j = varint(rec, j, (int)hs, &types[nt]); if (j < 0) break; nt++; }
                if (j < 0 || nt != NCOL) continue;
                uint64_t t_uid = types[1], t_dl = types[14];
                if (!(t_uid >= 13 && (t_uid & 1)) || !(t_dl >= 13 && (t_dl & 1))) continue;
                uint64_t uidlen = (t_uid - 13) / 2, dllen = (t_dl - 13) / 2;
                if (dllen != 51 + uidlen + (uint64_t)ndig(rowid)) continue;   /* not a video */
                videos++;
                if (!ov) { emit(rowid, rec, L); continue; }
                Pend *e = calloc(1, sizeof(Pend));
                e->rowid = rowid; e->P = P; e->next = ov; e->buf = malloc(P + 8);
                memcpy(e->buf, rec, L); e->used = L;
                advance(e);
            }
        }
        cur_pg++; pages++;
    }
    for (int h = 0; h < HT; h++) if (pend[h]) emit_unres(pend[h]);
    fprintf(stderr, "#DONE pages=%llu videos=%llu\n", (unsigned long long)pages, (unsigned long long)videos);
    return 0;
}
