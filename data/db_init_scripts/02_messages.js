print("Initializing messages collection...");

use("main");

db.createCollection("messages");

db.createView("messages_with_author", "messages", [
  {
    $lookup: {
      from: "actors",
      localField: "author_id",
      foreignField: "_id",
      as: "author",
    },
  },
  {
    $unwind: "$author",
  },
  {
    $unset: ["author_id"],
  },
]);
