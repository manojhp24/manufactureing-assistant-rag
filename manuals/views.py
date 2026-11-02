from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from accounts.permissions import administrator_required
from .forms import ManualUploadForm
from .models import Manual
from .services import index_manual


@login_required
@administrator_required
def upload_manual(request):

    if request.method == "POST":
        form = ManualUploadForm(request.POST, request.FILES)

        if form.is_valid():
            manual = form.save(commit=False)
            manual.save()

            try:
                index_manual(manual)

                messages.success(
                    request,
                    "Manual uploaded and indexed successfully."
                )

            except Exception as error:
                messages.error(
                    request,
                    f"Manual uploaded, but indexing failed: {error}"
                )

            return redirect("manual_list")

    else:
        form = ManualUploadForm()

    return render(
        request,
        "manuals/upload.html",
        {"form": form}
    )


@login_required
@administrator_required
def manual_list(request):

    manuals = Manual.objects.select_related("machine").all()

    return render(
        request,
        "manuals/list.html",
        {"manuals": manuals}
    )