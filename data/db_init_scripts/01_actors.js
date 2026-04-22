print("Initializing actors collection...");

use('main');

try {
    db.actors.insertMany([
        {
            "created_at": new Date("2026-02-02T03:01:29.371+00:00"),
            "last_active_at": new Date("2026-02-02T03:01:29.371+00:00"),
            "name": "Default",
            "role": "user"
        },
        {
            "created_at": new Date("2026-02-02T03:01:29.371+00:00"),
            "last_active_at": new Date("2026-02-02T03:01:29.371+00:00"),
            "name": "AutoMAESTRO",
            "role": "assistant"
        }
    ])

    print("Created " + db.actors.countDocuments() + " actors in the actors collection");
} catch (error) {
    print("Actors already created");
}

try {
    db.actors.createIndex({ "name": 1 }, { unique: true });
    db.actors.createIndex({ "active_conversation_id": 1 });

    print("Created indexes on actors collection");
} catch (error) {
    print("Actors collection already created");
}
