# ClipForge --- Audit dan Perbaikan Dashboard End-to-End

## Konteks

Saat project ClipForge dijalankan di `localhost:3000`, halaman yang
muncul hanya berupa teks dan elemen HTML dasar: judul "ClipForge Next.js
Dashboard", input URL, tombol "Generate Clips", dan satu contoh item
review. Tampilan tidak terlihat seperti dashboard Next.js + Tailwind
yang dijelaskan dalam laporan implementasi. Ini mengindikasikan bahwa
hasil yang diklaim selesai belum sesuai dengan pengalaman pengguna yang
diharapkan, atau halaman yang dijalankan bukan entrypoint/aplikasi yang
benar.

**Tujuan utama:** perbaiki project berdasarkan kondisi kode dan
spesifikasi yang benar-benar ada, sehingga pengguna dapat memasukkan
link video/VOD, menjalankan proses generate clip, melihat status proses,
lalu meninjau hasil clip melalui UI yang layak dan responsif.

Jangan langsung melakukan redesign atau menambahkan fitur secara acak.
Audit spesifikasi, konstitusi project, scope, struktur repo, dan
implementasi yang ada terlebih dahulu.

## Instruksi Wajib

### 1. Baca aturan dan scope sebelum mengubah kode

Sebelum membuat perubahan:

1.  Temukan dan baca `constitution.md` / `constitutional.md` yang
    berlaku untuk project. Periksa ejaan nama file dan lokasi
    sebenarnya; jangan mengasumsikan nama atau path.
2.  Baca dokumen project scope, PRD, roadmap, phase plan, README, serta
    instruksi lokal lain yang relevan seperti `AGENTS.md`.
3.  Periksa instruksi pada direktori root dan direktori aplikasi
    frontend/backend yang akan disentuh.
4.  Jika ada dokumen yang saling bertentangan, jelaskan konflik dan
    ikuti aturan prioritas yang ditentukan oleh project. Jangan
    diam-diam mengubah scope atau mengabaikan konstitusi.
5.  Buat ringkasan singkat tentang tujuan produk, fitur yang memang
    termasuk scope saat ini, arsitektur yang diwajibkan, dan acceptance
    criteria sebelum mulai implementasi.

**Jangan mengklaim sudah membaca dokumen jika file tersebut tidak
ditemukan atau tidak berhasil dibaca.** Laporkan nama/path yang dicari
dan lanjutkan hanya dengan asumsi yang diberi label jelas.

### 2. Audit penyebab UI tampil seperti HTML polos

Reproduksi masalah dari cara project benar-benar dijalankan. Periksa:

-   Apakah `localhost:3000` menjalankan aplikasi Next.js yang benar,
    bukan server lain, build lama, atau halaman placeholder.
-   Struktur repo dan entrypoint route yang aktif, termasuk `app/`,
    `pages/`, layout, dan komponen halaman.
-   Apakah Tailwind CSS terpasang dan dikonfigurasi dengan benar:
    dependency, konfigurasi, global CSS, import CSS pada root layout,
    serta content/source paths sesuai versi yang digunakan.
-   Apakah stylesheet dan aset benar-benar dimuat di browser; cek
    terminal, network/console bila tersedia, dan error build/runtime.
-   Apakah halaman yang tampil hanya scaffold/placeholder yang belum
    pernah diganti, atau implementasi dashboard sebenarnya berada di
    route lain.
-   Apakah dependency, konfigurasi Next.js, atau CSS mengalami regresi.
-   Apakah backend API tersedia dan endpoint yang dipanggil frontend
    cocok dengan API yang benar-benar diimplementasikan.

Jangan menutupi gejala dengan menambahkan CSS seadanya. Temukan root
cause, perbaiki, lalu verifikasi melalui build, test, dan browser/dev
server jika tool tersedia.

### 3. Implementasikan UI yang benar-benar usable

Setelah audit, bangun atau perbaiki dashboard sesuai konstitusi dan
scope project. Prioritas alur utama:

1.  **Submit video/VOD**
    -   Form input yang jelas untuk URL video/VOD yang didukung project.
    -   Validasi URL dan pesan error yang mudah dipahami.
    -   Tombol utama **Generate Clips** dengan state idle,
        loading/processing, disabled saat request berjalan, sukses, dan
        gagal.
    -   Cegah double submission.
    -   Jangan menyatakan proses berhasil sebelum backend mengonfirmasi.
2.  **Status pekerjaan**
    -   Tampilkan status yang benar-benar berasal dari backend, misalnya
        queued, processing, completed, atau failed, hanya jika status
        tersebut memang didukung oleh model/API.
    -   Jika proses asynchronous, gunakan mekanisme polling atau refresh
        yang sesuai dengan arsitektur yang sudah ada.
    -   Tampilkan error/actionable message saat backend tidak tersedia;
        jangan mengganti kegagalan dengan data sukses palsu.
3.  **Generated Clips / Review Queue**
    -   Tampilkan hasil nyata dari API atau sumber data yang digunakan
        project.
    -   Setiap clip menampilkan informasi yang memang tersedia, seperti
        judul, durasi, skor, status review, dan preview/video player
        jika file hasilnya tersedia.
    -   Sediakan tindakan review yang sesuai dengan backend:
        approve/publish dan reject.
    -   Berikan loading, empty, error, dan success states yang jelas.
    -   Jangan menampilkan contoh "Epic Stream Highlight #1" seolah-olah
        hasil nyata jika itu hanya mock data. Jika mock data memang
        dipakai untuk development, tandai dengan jelas dan pisahkan dari
        mode data nyata.
4.  **Visual design dan responsive layout**
    -   Implementasikan dashboard modern, konsisten, dan mudah dibaca
        sesuai arah desain dalam scope/konstitusi.
    -   Gunakan styling system yang sudah ditentukan project; jangan
        menambahkan UI framework baru tanpa alasan kuat.
    -   Pastikan desktop, tablet, dan mobile dapat digunakan. Form,
        kartu clip, status, dan tombol tidak boleh overflow atau
        terpotong.
    -   Gunakan hierarchy yang jelas, spacing konsisten, kontras teks
        yang baik, hover/focus states yang terlihat, serta indikator
        keyboard focus.
    -   Jika scope mengharuskan dark mode, implementasikan secara benar;
        jangan menganggap dark mode wajib jika tidak ada di spesifikasi.
5.  **Integrasi backend**
    -   Telusuri endpoint dan kontrak API yang benar-benar tersedia
        sebelum menghubungkannya.
    -   Cocokkan payload, response, status code, dan error handling
        frontend dengan backend.
    -   Jangan mengarang endpoint atau menganggap integrasi Clippo.id
        sudah berfungsi hanya karena disebut "ready" dalam laporan.
    -   Bila fitur belum tersedia, identifikasi gap secara eksplisit dan
        implementasikan hanya yang sesuai scope. Jangan membuat
        integrasi eksternal palsu.
    -   Pertahankan human approval sebelum publishing jika itu aturan
        project.

### 4. Jaga scope dan kualitas implementasi

-   Jangan melakukan rewrite besar-besaran jika perbaikan terarah sudah
    cukup.
-   Jangan menghapus fitur, file, data, atau konfigurasi tanpa alasan
    yang jelas.
-   Jangan menambahkan library baru jika solusi yang ada sudah memadai.
-   Ikuti pola arsitektur, naming, error handling, dan coding
    conventions project.
-   Jangan hardcode hasil sukses, status proses, atau daftar clip palsu
    ke production UI.
-   Jangan melemahkan validasi, approval gate, atau mekanisme keamanan
    yang sudah ditentukan.
-   Jangan menyentuh secret/API key atau menaruhnya di client-side code.
-   Jika ada perubahan di luar scope yang diperlukan, jelaskan alasannya
    dan minta persetujuan sebelum melakukannya.

## Urutan Kerja

Lakukan langkah-langkah ini secara berurutan:

1.  **Inspect:** cek working tree/status Git, struktur repo, instruksi
    project, konstitusi, scope, dan entrypoint yang berjalan.
2.  **Diagnose:** reproduksi masalah dan tentukan root cause mengapa UI
    tampil seperti HTML polos.
3.  **Plan:** tulis rencana singkat yang menghubungkan temuan audit
    dengan acceptance criteria. Bedakan bug yang terkonfirmasi dari
    dugaan.
4.  **Implement:** perbaiki root cause dan selesaikan alur submit →
    processing/status → hasil clip → review sesuai scope.
5.  **Verify:** jalankan test, lint, typecheck, dan production build
    yang tersedia. Jalankan backend/frontend dengan cara yang benar dan
    verifikasi route dashboard. Jika browser automation tersedia,
    periksa desktop dan mobile viewport.
6.  **Regression check:** pastikan pipeline backend, endpoint, approval
    gate, dan fitur yang sudah ada tidak rusak.
7.  **Report:** rangkum root cause, file yang diubah, fitur yang
    benar-benar bekerja, perintah verifikasi dan hasilnya, serta gap
    yang masih belum selesai.

Jangan berhenti setelah halaman terlihat bagus. Alur utamanya harus
benar-benar tersambung ke backend sejauh implementasi project
mendukungnya.

## Acceptance Criteria

Pekerjaan baru dianggap selesai jika:

-   [ ] Konstitusi dan project scope telah diperiksa; setiap batasan
    yang relevan dipatuhi.
-   [ ] Root cause tampilan HTML polos ditemukan dan diperbaiki, bukan
    sekadar ditutupi.
-   [ ] Route utama menampilkan dashboard yang ter-styling dengan benar,
    bukan HTML default/placeholder.
-   [ ] Pengguna dapat memasukkan URL video/VOD yang didukung dan
    menekan **Generate Clips**.
-   [ ] Form melakukan validasi dan menunjukkan loading/error/success
    state berdasarkan hasil request sebenarnya.
-   [ ] Frontend menggunakan endpoint dan kontrak API yang diverifikasi
    dari kode backend.
-   [ ] Status pekerjaan dan review queue menggunakan data nyata; mock
    data diberi label dan tidak disamarkan sebagai hasil asli.
-   [ ] Approve/reject terhubung ke mekanisme backend yang benar dan
    publishing tetap dilindungi human approval.
-   [ ] Layout tetap usable pada desktop dan mobile.
-   [ ] Test, lint, typecheck, dan build yang relevan dijalankan; hasil
    aktual dilaporkan dengan jujur.
-   [ ] Tidak ada klaim bahwa fitur bekerja jika belum diverifikasi.

## Format Laporan Akhir

Berikan laporan ringkas dengan bagian:

1.  **Dokumen yang dibaca** --- path konstitusi, scope, dan instruksi
    lain.
2.  **Root cause** --- penyebab spesifik UI polos beserta bukti.
3.  **Perubahan** --- file dan tujuan setiap perubahan penting.
4.  **Alur yang sudah berfungsi** --- submit, proses, hasil clip,
    review, dan publishing; bedakan yang terverifikasi dari yang belum.
5.  **Verifikasi** --- perintah yang dijalankan dan hasil aktual.
6.  **Gap tersisa** --- blocker, mock/integrasi yang belum tersedia,
    atau keputusan yang perlu persetujuan.

Mulai dengan audit, bukan langsung coding. Jangan menyatakan ClipForge
"fully realized", "production-ready", atau "thoroughly tested" kecuali
semua klaim tersebut benar-benar dibuktikan dari implementasi dan hasil
verifikasi.
