-- ASA v2 Knowledge Graph Schema
-- Run once against PostgreSQL to set up graph + vector tables

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Research sources (papers, articles)
CREATE TABLE IF NOT EXISTS research_sources (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title        TEXT NOT NULL,
    authors      JSONB DEFAULT '[]',
    journal      VARCHAR(500),
    doi          VARCHAR(255) UNIQUE,
    url          TEXT,
    abstract     TEXT,
    year         INT,
    citation_apa TEXT,
    topics       JSONB DEFAULT '[]',
    methods      JSONB DEFAULT '[]',
    full_text    TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Vector embeddings (pgvector)
CREATE TABLE IF NOT EXISTS research_embeddings (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id    UUID REFERENCES research_sources(id) ON DELETE CASCADE,
    chunk_text  TEXT NOT NULL,
    chunk_index INT,
    embedding   vector(1536),
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index for fast ANN search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON research_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Knowledge graph: nodes
CREATE TABLE IF NOT EXISTS kg_nodes (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id  UUID REFERENCES research_sources(id),
    node_type  VARCHAR(50) NOT NULL,  -- Paper, Author, Institution, Method, Dataset, Topic, Journal
    name       TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_name ON kg_nodes USING gin(to_tsvector('english', name));

-- Knowledge graph: edges
CREATE TABLE IF NOT EXISTS kg_edges (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_node_id UUID REFERENCES kg_nodes(id) ON DELETE CASCADE,
    target_node_id UUID REFERENCES kg_nodes(id) ON DELETE CASCADE,
    edge_type      VARCHAR(100) NOT NULL,  -- AUTHORED_BY, CITES, USES_METHOD, RELATED_TO_TOPIC
    weight         FLOAT DEFAULT 1.0,
    properties     JSONB DEFAULT '{}',
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_type   ON kg_edges(edge_type);

-- DOM knowledge graph (cached LMS selectors)
CREATE TABLE IF NOT EXISTS dom_graphs (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site       VARCHAR(100) NOT NULL,
    lms_url    TEXT,
    page_type  VARCHAR(100),
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    metadata   JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS dom_selectors (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    graph_id      UUID REFERENCES dom_graphs(id) ON DELETE CASCADE,
    key           VARCHAR(100),
    selector      TEXT,
    selector_type VARCHAR(30) DEFAULT 'css',
    fallbacks     JSONB DEFAULT '[]',
    last_verified TIMESTAMPTZ DEFAULT NOW()
);

-- Semantic search function
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count     INT DEFAULT 10
)
RETURNS TABLE (
    id         UUID,
    paper_id   UUID,
    chunk_text TEXT,
    similarity FLOAT,
    metadata   JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        re.id,
        re.paper_id,
        re.chunk_text,
        1 - (re.embedding <=> query_embedding) AS similarity,
        re.metadata
    FROM research_embeddings re
    WHERE 1 - (re.embedding <=> query_embedding) > match_threshold
    ORDER BY re.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
