#!/usr/bin/env python3
"""
Seed a realistic userbase into the ZIMA database.

Why this exists: per Frost's explicit ask, the frontend should NOT be built
against hardcoded mock arrays baked into frontend code — the actual database
infrastructure should be filled with a realistic userbase so that things
like account deletion and data export can be tested against real-shaped
data (real connection graphs, real project rosters, real message threads)
without any of it being fake at the frontend layer.

Usage:
    python -m scripts.seed_data                  # seed on top of existing data
    python -m scripts.seed_data --reset           # wipe all seed-relevant tables first
    python -m scripts.seed_data --profiles 500    # override profile count (default 300)
    python -m scripts.seed_data --seed 42          # reproducible run (default: 42)

Idempotency: --reset truncates every table this script owns (everything
except alembic_version) before seeding, so re-running with --reset always
produces a clean, reproducible dataset. Without --reset, profiles are
skipped if a profile with the same discord_id already exists (safe to
re-run to top up connections/projects/messages on an existing dataset).
"""

import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from faker import Faker  # noqa: E402

from src.database.models import (  # noqa: E402
    Connection,
    ConnectionStatusEnum,
    ConsentRecord,
    Event,
    Message,
    NeurotypeEnum,
    Organization,
    Profile,
    Project,
    ProjectParticipant,
    Resource,
    RoleGrant,
)
from src.db.session import engine, session_scope  # noqa: E402

# Per-archetype skill pools, taken directly from Archetypes.md so seeded
# profiles are the same taxonomy the product actually uses.
ARCHETYPE_SKILLS = {
    "seedcaster": ["regenerative agriculture", "composting", "food forests", "urban farming", "seed saving", "agroforestry"],
    "fabricant": ["mechanical engineering", "fabrication", "prototyping", "CAD/CAM", "open-source hardware", "maker culture"],
    "mycelian": ["biology", "chemistry", "biomaterials", "fermentation", "ecological science", "bioremediation"],
    "terraformer": ["sustainable architecture", "passive design", "urban ecology", "community land trusts", "natural building"],
    "developer": ["software engineering", "AI/ML", "data pipelines", "web dev", "automation", "prompt engineering"],
    "artisan": ["visual design", "fabrication", "textile/material work", "UI/UX", "solarpunk aesthetics", "world-building"],
    "chronicler": ["storytelling", "video production", "writing", "social media", "community media", "archiving"],
    "cultivar": ["food science", "plant medicine", "nutrition systems", "crop research", "soil biology"],
    "loomkeeper": ["community building", "event production", "fundraising", "partnerships", "grassroots organizing"],
    "verdant": ["policy", "advocacy", "circular economics", "environmental law", "systems governance", "funding strategy"],
}

# City hubs lifted from demo/zima-globe.html's CITY table so seeded locations
# match the geography the eventual map UI already expects.
CITIES = [
    "Nairobi", "Montreal", "Lagos", "Berlin", "Tokyo", "London", "Sydney", "Bangalore",
    "Austin", "Shenzhen", "Beijing", "Shanghai", "Toronto", "Monterrey", "Guadalajara",
    "Mexico City", "São Paulo", "Paris", "Vancouver", "Dakar", "Stockholm", "Brooklyn",
    "Oxford", "Bangkok", "Nairobi",
]

PROJECT_STATUSES = ["idea", "building", "launched"]
RESOURCE_TYPES = ["learning", "tool", "builder", "hackathon", "event", "dataset", "pattern", "lesson"]
ORG_TYPES = ["hardware", "advocacy", "employment", "finance", "infrastructure", "research", "education"]


def build_profile(fake: Faker, index: int) -> Profile:
    archetype = random.choice(list(ARCHETYPE_SKILLS.keys()))
    skills = random.sample(ARCHETYPE_SKILLS[archetype], k=min(3, len(ARCHETYPE_SKILLS[archetype])))
    other_pool = [s for arch, pool in ARCHETYPE_SKILLS.items() if arch != archetype for s in pool]
    offering = random.sample(skills + random.sample(other_pool, 2), k=2)
    looking_for = random.sample(other_pool, k=2)
    display_name = fake.name()
    discord_id = str(100000000000000000 + index)  # snowflake-shaped, deterministic per index

    return Profile(
        id=uuid.uuid4(),
        discord_id=discord_id,
        discord_username=fake.user_name(),
        display_name=display_name,
        location=random.choice(CITIES),
        skills=skills,
        bio=fake.paragraph(nb_sentences=3),
        links=[f"https://github.com/{fake.user_name()}"],
        onboarding_completed_at=fake.date_time_between(start_date="-6M", end_date="now", tzinfo=timezone.utc),
        neurotype=archetype if random.random() > 0.05 else None,  # ~5% haven't taken the quiz yet
        offering=offering,
        looking_for=looking_for,
        projects=[],
        is_open=random.random() > 0.15,
        tagline=fake.catch_phrase(),
        vision_2036=fake.sentence(nb_words=12),
        mission=fake.sentence(nb_words=10),
        badges=random.sample(["early-adopter", "verified", "mentor", "hackathon-winner"], k=random.randint(0, 2)),
        wall_posts=[],
        consented_at=fake.date_time_between(start_date="-6M", end_date="now", tzinfo=timezone.utc),
    )


def seed(profiles_count: int, seed_value: int, reset: bool) -> None:
    random.seed(seed_value)
    fake = Faker()
    Faker.seed(seed_value)

    if reset:
        print("--reset: truncating all seed-owned tables...")
        with engine.begin() as conn:
            for table in [
                "deletion_audit_log",
                "deletion_requests",
                "consent_records",
                "messages",
                "project_participants",
                "projects",
                "connections",
                "role_grants",
                "quest_completions",
                "resources",
                "events",
                "organizations",
                "profiles",
            ]:
                conn.exec_driver_sql(f'TRUNCATE TABLE "{table}" CASCADE')
        print("...done.")

    with session_scope() as db:
        existing = {p.discord_id for p in db.query(Profile.discord_id).all()}

        profiles = []
        for i in range(profiles_count):
            profile = build_profile(fake, i)
            if profile.discord_id in existing:
                continue
            db.add(profile)
            profiles.append(profile)
        db.flush()
        print(f"Seeded {len(profiles)} profiles.")

        # Consent record per profile.
        for p in profiles:
            db.add(
                ConsentRecord(
                    id=uuid.uuid4(),
                    profile_id=p.id,
                    consent_type="data_processing",
                    granted_at=p.consented_at,
                    source="discord_onboarding",
                )
            )

        # Role grants (mirrors what the Discord bot writes on real onboarding).
        for p in profiles:
            db.add(RoleGrant(id=uuid.uuid4(), discord_id=p.discord_id, role_key="vetted", source="onboarding"))

        # Organizations.
        orgs = []
        for _ in range(max(5, profiles_count // 8)):
            org = Organization(
                id=uuid.uuid4(),
                name=f"{fake.company()} {random.choice(['Collective', 'Co-op', 'Initiative', 'Network', 'Lab'])}",
                mission=fake.sentence(nb_words=15),
                location=random.choice(CITIES),
                org_type=random.choice(ORG_TYPES),
                roles_open=random.sample(["engineer", "organizer", "designer", "researcher", "volunteer"], k=2),
                email=fake.company_email(),
                resume_request=random.random() > 0.5,
                trust_score=round(random.uniform(0.4, 0.95), 2),
            )
            db.add(org)
            orgs.append(org)
        db.flush()
        print(f"Seeded {len(orgs)} organizations.")

        # Projects, owned by a random subset of profiles.
        projects = []
        if profiles:
            for _ in range(max(10, profiles_count // 5)):
                owner = random.choice(profiles)
                project = Project(
                    id=uuid.uuid4(),
                    owner_id=owner.id,
                    title=fake.catch_phrase(),
                    description=fake.paragraph(nb_sentences=4),
                    neurotypes_needed=random.sample(list(ARCHETYPE_SKILLS.keys()), k=2),
                    skills_needed=random.sample(sum(ARCHETYPE_SKILLS.values(), []), k=3),
                    status=random.choice(PROJECT_STATUSES),
                )
                db.add(project)
                projects.append(project)
            db.flush()

            for project in projects:
                db.add(ProjectParticipant(id=uuid.uuid4(), project_id=project.id, profile_id=project.owner_id, role="owner"))
                for participant in random.sample(profiles, k=min(random.randint(0, 4), len(profiles))):
                    if participant.id == project.owner_id:
                        continue
                    db.add(
                        ProjectParticipant(
                            id=uuid.uuid4(), project_id=project.id, profile_id=participant.id, role="contributor"
                        )
                    )
        print(f"Seeded {len(projects)} projects with rosters.")

        # Connections between random profile pairs.
        connection_count = 0
        seen_pairs = set()
        if len(profiles) >= 2:
            target_connections = max(20, profiles_count * 3)
            attempts = 0
            while connection_count < target_connections and attempts < target_connections * 5:
                attempts += 1
                a, b = random.sample(profiles, 2)
                pair = (a.id, b.id)
                if pair in seen_pairs or (b.id, a.id) in seen_pairs:
                    continue
                seen_pairs.add(pair)
                db.add(
                    Connection(
                        id=uuid.uuid4(),
                        from_user_id=a.id,
                        to_user_id=b.id,
                        status=random.choice([s.value for s in ConnectionStatusEnum]),
                        message=fake.sentence(nb_words=10),
                    )
                )
                connection_count += 1
        print(f"Seeded {connection_count} connections.")

        # Messages between connected pairs.
        message_count = 0
        for (a_id, b_id) in list(seen_pairs)[: max(30, profiles_count * 2)]:
            for _ in range(random.randint(1, 4)):
                sender, recipient = random.choice([(a_id, b_id), (b_id, a_id)])
                db.add(
                    Message(
                        id=uuid.uuid4(),
                        from_user_id=sender,
                        to_user_id=recipient,
                        content=fake.sentence(nb_words=random.randint(5, 20)),
                        read=random.random() > 0.4,
                        created_at=fake.date_time_between(start_date="-3M", end_date="now", tzinfo=timezone.utc),
                    )
                )
                message_count += 1
        print(f"Seeded {message_count} messages.")

        # Resources (directory), a subset submitted by profiles.
        resource_count = 0
        for _ in range(max(15, profiles_count // 6)):
            db.add(
                Resource(
                    id=uuid.uuid4(),
                    title=fake.sentence(nb_words=6).rstrip("."),
                    type=random.choice(RESOURCE_TYPES),
                    category=random.choice(["Agriculture", "Green tech", "Technology", "Community"]),
                    url=fake.url(),
                    description=fake.sentence(nb_words=14),
                    status=random.choice(["pending", "verified"]),
                    votes=random.randint(0, 300),
                    cool=random.randint(0, 150),
                    submitted_by=random.choice(profiles).id if profiles and random.random() > 0.2 else None,
                )
            )
            resource_count += 1
        print(f"Seeded {resource_count} resources.")

        # Events.
        event_count = 0
        for _ in range(8):
            db.add(
                Event(
                    id=uuid.uuid4(),
                    title=f"{fake.catch_phrase()} {random.choice(['Build Weekend', 'Meetup', 'Hackathon'])}",
                    date=fake.date_time_between(start_date="now", end_date="+3M", tzinfo=timezone.utc),
                    location=random.choice(CITIES),
                    official=random.random() > 0.6,
                    description=fake.sentence(nb_words=16),
                    contact_email=fake.company_email(),
                )
            )
            event_count += 1
        print(f"Seeded {event_count} events.")

    print("Seed complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profiles", type=int, default=300, help="Number of profiles to seed (default: 300)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--reset", action="store_true", help="Truncate all seed-owned tables before seeding")
    parser.add_argument("--force", action="store_true", help="Override the production safety guard (dangerous)")
    args = parser.parse_args()

    # Refuse to fabricate synthetic users into a production database. This script
    # is a dev/test seeder; running it against real signups would corrupt data.
    from src.core.config import get_settings

    if get_settings().is_production and not args.force:
        print(
            "REFUSING to seed: ENVIRONMENT=production. This generates synthetic users and is "
            "dev/test only. Re-run with --force only if you are absolutely certain.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Fail loudly rather than seeding into an unmigrated database.
    from sqlalchemy import inspect

    inspector = inspect(engine)
    if "profiles" not in inspector.get_table_names():
        print("ERROR: 'profiles' table does not exist. Run `alembic upgrade head` first.", file=sys.stderr)
        sys.exit(1)

    seed(args.profiles, args.seed, args.reset)


if __name__ == "__main__":
    main()
