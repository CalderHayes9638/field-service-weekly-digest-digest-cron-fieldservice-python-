from field_digest.digest_service import DigestRequest, build_digest


def test_digest_keeps_active_dispatch_and_due_follow_up() -> None:
    request = DigestRequest.model_validate(
        {
            "audience_email": "dispatch@example.com",
            "as_of": "2026-09-07T13:00:00Z",
            "work_orders": [
                {
                    "work_order_id": "WO-104",
                    "site_name": "North Clinic",
                    "technician_name": "Mina",
                    "dispatch_status": "complete",
                    "photos": [
                        {
                            "photo_id": "P-9",
                            "captured_at": "2026-09-05T10:00:00Z",
                            "caption": "Panel after repair",
                        }
                    ],
                    "follow_up": {
                        "required": True,
                        "completed": False,
                        "due_at": "2026-09-07T12:00:00Z",
                    },
                },
                {
                    "work_order_id": "WO-105",
                    "site_name": "West Depot",
                    "technician_name": "Owen",
                    "dispatch_status": "on_site",
                    "photos": [],
                    "follow_up": {"required": False, "completed": False},
                },
                {
                    "work_order_id": "WO-106",
                    "site_name": "South School",
                    "dispatch_status": "complete",
                    "photos": [],
                    "follow_up": {"required": True, "completed": True},
                },
            ],
        }
    )

    result = build_digest(request)

    assert [item.work_order_id for item in result.items] == ["WO-104", "WO-105"]
    assert result.items[0].follow_up_due is True
    assert result.items[0].photo_count == 1
    assert result.items[1].dispatch_status.value == "on_site"
