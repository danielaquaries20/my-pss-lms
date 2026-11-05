# Fitur Manajemen Kursus dan Komentar

## Overview fitur

Fitur ini menambahkan dua halaman baca-saja pada e-LMS Kulino:

- `/kursus/` menampilkan semua kursus beserta deskripsi, username pengajar, harga, dan daftar subscriber. Setiap subscriber ditampilkan dengan username serta badge peran **Siswa** atau **Asisten**.
- `/komentar/` menampilkan komentar terbaru terlebih dahulu. Setiap kartu diskusi memuat username penulis, nama kursus, judul konten, isi komentar, dan waktu komentar.

Dua tombol pada `home.html` juga diarahkan ulang dari `/admin/` ke halaman yang sesuai:

- **Manajemen Kursus** → `/kursus/`
- **Komentar & Diskusi** → `/komentar/`

## File yang ditambah dan diubah

- `my-pss-lms/code/core/views.py` — menambahkan view baca-saja `manajemen_kursus` dan `komentar_diskusi` beserta query relasinya.
- `my-pss-lms/code/core/urls.py` — mendaftarkan route `/kursus/` dan `/komentar/`.
- `my-pss-lms/code/core/templates/core/manajemen_kursus.html` — halaman baru untuk daftar kursus dan subscriber dengan tema navy/gold.
- `my-pss-lms/code/core/templates/core/komentar_diskusi.html` — halaman baru untuk daftar komentar dan konteks diskusi dengan tema navy/gold.
- `my-pss-lms/code/core/templates/core/home.html` — mengubah tujuan dua tombol menu dari `/admin/` ke route baru.
- `my-pss-lms/docs/fitur-manajemen-kursus-dan-komentar.md` — dokumentasi implementasi dan verifikasi fitur.

## Kode penting

### View functions

Kode berikut berasal dari `code/core/views.py`:

```python
def manajemen_kursus(request):
    courses = Course.objects.prefetch_related(
        "coursemember_set__user_id", "teacher"
    )
    return render(request, "core/manajemen_kursus.html", {"courses": courses})


def komentar_diskusi(request):
    comments = Comment.objects.select_related(
        "member_id__user_id", "content_id__course_id"
    ).order_by("-created_at")
    return render(request, "core/komentar_diskusi.html", {"comments": comments})
```

### URL patterns

Route berikut ditambahkan pada `code/core/urls.py`:

```python
path("kursus/", views.manajemen_kursus, name="manajemen_kursus"),
path("komentar/", views.komentar_diskusi, name="komentar_diskusi"),
```

### Loop kursus dan subscriber

Bagian utama pada `code/core/templates/core/manajemen_kursus.html`:

```django-html
{% for course in courses %}
<section class="course-card">
    <h2 class="course-title">{{ course.name }}</h2>
    <p class="course-desc">{{ course.description }}</p>
    <div class="course-meta">
        <span><strong>Pengajar:</strong> {{ course.teacher.username }}</span>
        <span><strong>Harga:</strong> Rp {{ course.price }}</span>
    </div>

    <h3 class="subscriber-heading">Daftar Subscriber</h3>
    {% for member in course.coursemember_set.all %}
    <div class="subscriber-item">
        <span class="subscriber-name">{{ member.user_id.username }}</span>
        <span class="badge-type{% if member.roles == 'ast' %} badge-assistant{% endif %}">
            {{ member.get_roles_display }}
        </span>
    </div>
    {% empty %}
    <p class="empty-state">Belum ada subscriber untuk kursus ini.</p>
    {% endfor %}
</section>
{% empty %}
<div class="empty-page">Belum ada kursus yang tersedia.</div>
{% endfor %}
```

`badge-type` menggunakan warna biru untuk peran Siswa. Class tambahan `badge-assistant` menggunakan warna gold untuk peran Asisten.

### Loop komentar

Bagian utama pada `code/core/templates/core/komentar_diskusi.html`:

```django-html
{% for item in comments %}
<article class="discussion-card">
    <div class="discussion-top">
        <h2 class="author">{{ item.member_id.user_id.username }}</h2>
        <time class="created-at">{{ item.created_at|date:"d M Y H:i" }}</time>
    </div>
    <div class="context">
        <span>{{ item.content_id.course_id.name }}</span>
        <span class="context-separator">&bull;</span>
        <span>{{ item.content_id.name }}</span>
    </div>
    <div class="comment-text">{{ item.comment|linebreaksbr }}</div>
</article>
{% empty %}
<div class="empty-state">Belum ada komentar atau diskusi.</div>
{% endfor %}
```

## Relasi model yang dipakai

### Course → CourseMember → User

`CourseMember.course_id` menghubungkan subscriber ke kursus, sedangkan `CourseMember.user_id` menghubungkannya ke user. Field `roles` menyimpan peran dengan pilihan Siswa atau Asisten. Pengajar kursus juga merupakan relasi langsung dari `Course.teacher` ke `User`.

Cuplikan field dari `code/core/models.py`:

```python
class Course(models.Model):
    name = models.CharField("nama matkul", max_length=100)
    description = models.TextField("deskripsi", default="-")
    price = models.IntegerField("harga", default=10000)
    image = models.ImageField("gambar", null=True, blank=True)
    teacher = models.ForeignKey(
        User, verbose_name="pengajar", on_delete=models.RESTRICT
    )


ROLE_OPTIONS = [("std", "Siswa"), ("ast", "Asisten")]


class CourseMember(models.Model):
    course_id = models.ForeignKey(
        Course, verbose_name="matkul", on_delete=models.RESTRICT
    )
    user_id = models.ForeignKey(User, verbose_name="siswa", on_delete=models.RESTRICT)
    roles = models.CharField("peran", max_length=3, choices=ROLE_OPTIONS, default="std")
```

### Comment → CourseMember dan CourseContent

`Comment.member_id` menyediakan akses ke penulis melalui `CourseMember.user_id`. `Comment.content_id` menyediakan judul materi dan akses ke kursus melalui `CourseContent.course_id`.

Cuplikan field dari `code/core/models.py`:

```python
class CourseContent(models.Model):
    name = models.CharField("judul konten", max_length=200)
    description = models.TextField("deskripsi", default="-")
    video_url = models.CharField("URL Video", max_length=200, null=True, blank=True)
    file_attachment = models.FileField("File", null=True, blank=True)
    course_id = models.ForeignKey(
        Course, verbose_name="matkul", on_delete=models.RESTRICT
    )


class Comment(models.Model):
    content_id = models.ForeignKey(
        CourseContent, verbose_name="konten", on_delete=models.CASCADE
    )
    member_id = models.ForeignKey(
        CourseMember, verbose_name="pengguna", on_delete=models.CASCADE
    )
    comment = models.TextField("komentar")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Cara mengakses dan verifikasi

Akses halaman melalui:

- Dashboard: `http://localhost:8007/`
- Manajemen Kursus: `http://localhost:8007/kursus/`
- Komentar & Diskusi: `http://localhost:8007/komentar/`

Karena verifikasi dijalankan pada Windows, output curl dibuang ke `NUL`. Pemeriksaan status yang dijalankan:

```console
$ curl -s -o NUL -w "%{http_code}\n" http://localhost:8007/kursus/
200

$ curl -s -o NUL -w "%{http_code}\n" http://localhost:8007/komentar/
200
```

Jumlah data diperiksa dari container Django:

```console
$ docker compose exec -T django python manage.py shell -c "from core.models import CourseMember, Comment; print(CourseMember.objects.count(), Comment.objects.count())"
3 1
```

Halaman kemudian disimpan dari respons HTTP untuk diperiksa isinya:

```console
$ curl -s http://localhost:8007/ -o "$TEMP/lms_home_verify.html"
$ curl -s http://localhost:8007/kursus/ -o "$TEMP/lms_kursus_verify.html"
$ curl -s http://localhost:8007/komentar/ -o "$TEMP/lms_komentar_verify.html"
```

Hasil pencarian pada respons HTML:

- Homepage memuat `location.href='/kursus/'` dan `location.href='/komentar/'`.
- Halaman kursus memuat seluruh tiga baris subscriber: `daniel`, `daniel`, dan `Ghiyatsi`, termasuk label peran `Siswa`.
- Halaman komentar memuat data komentar aktual: penulis `Ghiyatsi`, kursus `Ilmu Falak`, konten `Bermain Game`, dan komentar `Seru sekali permainannya`.

## Catatan desain

- Seluruh CSS berada di dalam elemen `<style>` pada masing-masing template baru. Tidak ada file CSS statis eksternal yang ditambahkan.
- Tema, token warna, top navigation, header banner, kartu, badge, dan footer mengikuti gaya `konten_list.html` dengan warna navy/gold dan font Plus Jakarta Sans.
- View kursus menggunakan `prefetch_related("coursemember_set__user_id", "teacher")` agar daftar subscriber dan data user tidak menimbulkan query N+1.
- View komentar menggunakan `select_related("member_id__user_id", "content_id__course_id")` agar data penulis, konten, dan kursus diambil melalui join, serta `order_by("-created_at")` agar komentar terbaru tampil lebih dahulu.
- Halaman kursus memiliki empty state untuk kursus tanpa subscriber dan untuk kondisi tanpa kursus. Halaman komentar memiliki empty state `Belum ada komentar atau diskusi.` ketika belum ada data.
- Kedua halaman hanya menampilkan data dan tidak menyediakan operasi tambah, ubah, atau hapus.

## Kustomisasi Tampilan Silk (/silk/)

Tampilan Django Silk memakai mekanisme override Django tanpa mengubah paket bawaan. Template `code/core/templates/silk/base/base.html` menyalin struktur `base.html` milik Silk, lalu menambahkan font Plus Jakarta Sans dan stylesheet tema Kulino. Override ini ditemukan lebih dahulu karena aplikasi `core` berada sebelum `silk` di `INSTALLED_APPS`.

Tema navy/gold berada di `code/static/silk/css/pages/kulino_theme.css` dan didaftarkan melalui `STATICFILES_DIRS` pada settings. Stylesheet tersebut dimuat setelah stylesheet halaman Silk agar aturan tema dapat mengganti tampilan tanpa mengubah class atau ID yang dipakai JavaScript Silk.

File di dalam `site-packages` tidak boleh diedit karena perubahan akan hilang ketika dependency atau container dibangun ulang. Jika versi Silk ditingkatkan dari 5.6.0, salinan template override perlu dibandingkan kembali dengan template upstream agar block dan struktur HTML tetap kompatibel.
