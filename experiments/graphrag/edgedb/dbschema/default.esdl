module default {
    type Concept {
        required node_id: str {
            constraint exclusive;
        };
        required label: str;
        required content: str;
        embedding: array<float64>;
        multi related_concepts: Concept;
    }
}
