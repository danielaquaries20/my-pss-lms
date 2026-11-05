import os
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse, FileResponse, Http404
from django.template import loader
from django.db.models import Max, Min, Avg, Count
from django.core import serializers
from .models import Course, CourseMember, CourseContent, Comment
from silk.profiling.profiler import silk_profile


def core(request):
    return render(request, "core/home.html")


def statistik(request):
    return render(request, "core/statistik.html")


def statistik_pengguna(request):
    return render(request, "core/statistik_pengguna.html")


def statistik_from_api(request):
    return render(request, "core/statistik_pengguna.html")


def users(request):
    myusers = User.objects.all().values()
    template = loader.get_template("all_users.html")
    context = {
        "myusers": myusers,
    }
    return HttpResponse(template.render(context, request))

@silk_profile(name='Profiling Statistik Kursus')
def courseStat(request):
    courses = Course.objects.all()
    stats = courses.aggregate(
        max_price=Max("price"), min_price=Min("price"), avg_price=Avg("price")
    )
    cheapest = Course.objects.filter(price=stats["min_price"])
    expensive = Course.objects.filter(price=stats["max_price"])

    popular = Course.objects.annotate(member_count=Count("coursemember")).order_by(
        "-member_count"
    )[:5]
    unpopular = Course.objects.annotate(member_count=Count("coursemember")).order_by(
        "member_count"
    )[:5]

    # Ubah format queryset menjadi list dictionary yang bersih dan sesuai dibaca JS
    cheapest_data = [{"id": c.id, "name": c.name, "price": c.price} for c in cheapest]
    expensive_data = [{"id": c.id, "name": c.name, "price": c.price} for c in expensive]

    popular_data = [
        {
            "id": c.id,
            "name": c.name,
            "price": c.price,
            "member_count": c.member_count,
        }
        for c in popular
    ]
    unpopular_data = [
        {
            "id": c.id,
            "name": c.name,
            "price": c.price,
            "member_count": c.member_count,
        }
        for c in unpopular
    ]

    result = {
        "course_count": courses.count(),
        "comment_count": Comment.objects.count(),
        "stats": stats,  # Key 'stats' agar dibaca oleh statistik_from_api.html
        "courses": stats,  # Key 'courses' tetap disediakan untuk halaman lain
        "cheapest": cheapest_data,
        "expensive": expensive_data,
        "popular": popular_data,
        "unpopular": unpopular_data,
    }
    return JsonResponse(result, safe=False)


@silk_profile(name='Profiling Statistik Pengguna')
def userStatistics(request):
    non_admin_users = User.objects.filter(is_staff=False, is_superuser=False)
    total_non_admin_users = non_admin_users.count()

    users_with_courses = non_admin_users.filter(
        id__in=CourseMember.objects.values_list("user_id", flat=True)
    ).distinct()
    total_users_with_courses = users_with_courses.count()

    users_without_courses = non_admin_users.exclude(
        id__in=users_with_courses.values_list("id", flat=True)
    )
    total_users_without_courses = users_without_courses.count()

    avg_courses_per_user = (
        CourseMember.objects.values("user_id")
        .annotate(total=Count("course_id"))
        .aggregate(avg_courses=Avg("total"))["avg_courses"]
        or 0
    )

    top_user = (
        CourseMember.objects.values("user_id")
        .annotate(total=Count("course_id"))
        .order_by("-total")
        .first()
    )
    top_user_data = {}
    if top_user:
        top_user_instance = User.objects.get(id=top_user["user_id"])
        top_user_data = {
            "id": top_user_instance.id,
            "username": top_user_instance.username,
            "email": top_user_instance.email,
            "total_courses": top_user["total"],
        }

    users_no_courses = non_admin_users.exclude(
        id__in=CourseMember.objects.values_list("user_id", flat=True)
    )
    users_no_courses_list = list(users_no_courses.values("id", "username", "email"))

    result = {
        "total_non_admin_users": total_non_admin_users,
        "total_users_with_courses": total_users_with_courses,
        "total_users_without_courses": total_users_without_courses,
        "average_courses_per_user": avg_courses_per_user,
        "top_user": top_user_data,
        "users_no_courses": users_no_courses_list,
    }
    return JsonResponse(result, safe=False)


# 1. Insert data User
def insert_user(request):
    user, created = User.objects.get_or_create(
        username="usertesting", defaults={"email": "usertest@email.com"}
    )

    if created:
        user.set_password("sanditesting")
        user.save()

    return JsonResponse(
        {
            "message": (
                "User berhasil ditambahkan" if created else "User sudah tersedia"
            ),
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )


# 2. Insert data Course
def insert_course(request):
    teacher = get_object_or_404(User, pk=1)

    course = Course.objects.create(
        name="Pemrograman Python",
        description="Belajar dasar pemrograman Python",
        price=150000,
        teacher=teacher,
    )

    return JsonResponse(
        {
            "message": "Course berhasil ditambahkan",
            "id": course.id,
            "name": course.name,
            "teacher": course.teacher.username,
        }
    )


# 3. Select semua User, tampilkan dalam HTML
def user_list(request):
    users = User.objects.all().order_by("id")
    return render(request, "users.html", {"users": users})


# 4. Select semua User, tampilkan sebagai JSON
def user_json(request):
    users = User.objects.all().values(
        "id", "username", "email", "first_name", "last_name"
    )
    return JsonResponse(list(users), safe=False)


# 5. Select satu User berdasarkan ID, tampilkan dalam HTML
def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    return render(request, "user_detail.html", {"user": user})


# 6. Select User dengan kondisi WHERE
def search_user(request):
    username = request.GET.get("username", "")
    users = User.objects.filter(username__icontains=username).order_by("id")

    return render(request, "users.html", {"users": users})


# 7. Update data User
@require_POST
def update_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.email = request.POST.get("email", user.email)
    user.save()

    return JsonResponse(
        {
            "message": "User berhasil diupdate",
            "id": user.id,
            "email": user.email,
        }
    )


# 8. Delete satu User
@require_POST
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    username = user.username
    user.delete()

    return JsonResponse({"message": f"User {username} berhasil dihapus"})


# 9. Delete semua Course
@require_POST
def delete_all_courses(request):
    total, details = Course.objects.all().delete()

    return JsonResponse(
        {
            "message": "Proses penghapusan Course selesai",
            "deleted_count": total,
            "details": details,
        }
    )


# 10. Delete semua User kecuali ID tertentu
@require_POST
def delete_users_except(request, pk):
    # Contoh: pertahankan user dengan ID pk
    users = User.objects.exclude(pk=pk)
    total, details = users.delete()

    return JsonResponse(
        {
            "message": f"User selain ID {pk} telah diproses",
            "deleted_count": total,
            "details": details,
        }
    )


@silk_profile(name='Profiling Kursus')
def allCourse(request):
    allCourse = Course.objects.all()
    result = []

    for course in allCourse:
        record = {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "price": course.price,
            "teacher": {
                "id": course.teacher.id,
                "username": course.teacher.username,
                "email": course.teacher.email,
                "fullname": f"{course.teacher.first_name} {course.teacher.last_name}",
            },
        }
        result.append(record)

    return JsonResponse(result, safe=False)


@silk_profile(name='Profiling Kursus Pengguna')
def userCourses(request):
    user = User.objects.get(pk=3)
    courses = Course.objects.filter(teacher=user.id)

    course_data = []
    for course in courses:
        record = {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "price": course.price,
        }
        course_data.append(record)

    result = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "fullname": f"{user.first_name} {user.last_name}",
        "courses": course_data,
    }

    return JsonResponse(result, safe=False)


@silk_profile(name='Profiling Statistik Pengguna')
def courseMemberStat(request):
    courses = Course.objects.filter(description__contains="Python").annotate(
        member_num=Count("coursemember")
    )
    course_data = []
    for course in courses:
        record = {
            "id": course.id,
            "name": course.name,
            "price": course.price,
            "member_count": course.member_num,
        }
        course_data.append(record)
    result = {"data_count": len(course_data), "data": course_data}
    return JsonResponse(result)


@silk_profile(name='Profiling Daftar Konten Kursus')
def content_list(request):
    courses = Course.objects.prefetch_related("coursecontent_set").all()
    return render(request, "core/konten_list.html", {"courses": courses})


@silk_profile(name='Profiling Manajemen Kursus')
def manajemen_kursus(request):
    courses = Course.objects.prefetch_related(
        "coursemember_set__user_id", "teacher"
    )
    return render(request, "core/manajemen_kursus.html", {"courses": courses})


@silk_profile(name='Profiling Komentar Diskusi')
def komentar_diskusi(request):
    comments = Comment.objects.select_related(
        "member_id__user_id", "content_id__course_id"
    ).order_by("-created_at")
    return render(request, "core/komentar_diskusi.html", {"comments": comments})


@silk_profile(name='Profiling Detail Konten Kursus')
def content_detail(request, pk):
    content = get_object_or_404(CourseContent, pk=pk)
    ext = content.file_extension

    is_image = ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]
    is_pdf = ext == ".pdf"
    is_ppt = ext in [".ppt", ".pptx"]
    is_video_file = ext in [".mp4", ".webm"]

    context = {
        "content": content,
        "is_image": is_image,
        "is_pdf": is_pdf,
        "is_ppt": is_ppt,
        "is_video_file": is_video_file,
    }
    return render(request, "core/konten_detail.html", context)


@silk_profile(name='Profiling Download Konten')
def download_content_file(request, pk):
    content = get_object_or_404(CourseContent, pk=pk)
    if not content.file_attachment:
        raise Http404("Konten ini tidak memiliki lampiran file.")

    file_path = content.file_attachment.path
    if os.path.exists(file_path):
        return FileResponse(open(file_path, "rb"), as_attachment=True)
    raise Http404("File fisik tidak ditemukan pada storage server.")
