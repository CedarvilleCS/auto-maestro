print("Initializing actors collection...");

use("main");

db.createCollection("conversations");

db.createView("conversations_with_messages_and_owner", "conversations", [
  {
    $lookup: {
      from: "actors",
      localField: "owner_id",
      foreignField: "_id",
      as: "owner",
    },
  },
  {
    $unwind: "$owner",
  },
  {
    $lookup: {
      from: "messages_with_author",
      localField: "_id",
      foreignField: "conversation_id",
      as: "messages",
    },
  },
  {
    $unset: "messages.conversation_id",
  },
  {
    $unset: "owner_id"
  },
]);
