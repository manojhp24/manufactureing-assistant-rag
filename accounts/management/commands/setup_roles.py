from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Create application user groups and map model permissions"

    def handle(self, *args, **options):
        role_definitions = {
            "Administrator": {
                "app_labels": ["machines", "manuals"],
                "specific_perms": [
                    ("auth", "view_user"),
                    ("auth", "add_user"),
                    ("auth", "change_user"),
                    ("auth", "view_group"),
                ],
            },
            "Supervisor": {
                "specific_perms": [
                    ("machines", "view_machine"),
                    ("machines", "change_machine"),
                    ("manuals", "view_manual"),
                ],
            },
            "Engineer": {
                "specific_perms": [
                    ("machines", "view_machine"),
                    ("manuals", "view_manual"),
                ],
            },
        }

        for role_name, config in role_definitions.items():
            group, created = Group.objects.get_or_create(name=role_name)

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group: {role_name}"))
            else:
                self.stdout.write(f"Group already exists: {role_name}")

            # Assign app-wide permissions if configured
            if "app_labels" in config:
                for app_label in config["app_labels"]:
                    perms = Permission.objects.filter(content_type__app_label=app_label)
                    group.permissions.add(*perms)

            # Assign specific permissions
            if "specific_perms" in config:
                for app_label, codename in config["specific_perms"]:
                    try:
                        perm = Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=codename
                        )
                        group.permissions.add(perm)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Permission not found: {app_label}.{codename}"
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS("Role groups and permissions setup completed.")
        )
