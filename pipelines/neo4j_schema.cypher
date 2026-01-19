// Neo4j 스키마 정의: 제약조건 및 인덱스

// ========================================
// 제약조건 (Constraints)
// ========================================

// Entity 노드의 id는 유니크해야 함
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// Component 노드의 id는 유니크해야 함
CREATE CONSTRAINT component_id_unique IF NOT EXISTS
FOR (c:Component) REQUIRE c.id IS UNIQUE;

// ErrorCode 노드의 code는 유니크해야 함
CREATE CONSTRAINT error_code_unique IF NOT EXISTS
FOR (ec:ErrorCode) REQUIRE ec.code IS UNIQUE;

// ========================================
// 인덱스 (Indexes)
// ========================================

// Entity 이름으로 빠른 검색
CREATE INDEX entity_name_index IF NOT EXISTS
FOR (e:Entity) ON (e.name);

// Entity 타입으로 필터링
CREATE INDEX entity_type_index IF NOT EXISTS
FOR (e:Entity) ON (e.type);

// Component 이름으로 검색
CREATE INDEX component_name_index IF NOT EXISTS
FOR (c:Component) ON (c.name);

// ErrorCode 검색
CREATE INDEX error_code_code_index IF NOT EXISTS
FOR (ec:ErrorCode) ON (ec.code);

// ========================================
// Full-text 인덱스 (전체 텍스트 검색)
// ========================================

// Entity 이름 및 설명에 대한 전체 텍스트 검색
CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description];

// Component 전체 텍스트 검색
CREATE FULLTEXT INDEX component_fulltext IF NOT EXISTS
FOR (c:Component) ON EACH [c.name, c.description];

// ErrorCode 메시지 전체 텍스트 검색
CREATE FULLTEXT INDEX error_fulltext IF NOT EXISTS
FOR (ec:ErrorCode) ON EACH [ec.code, ec.message, ec.description];

// ========================================
// 예제 쿼리
// ========================================

// 전체 텍스트 검색 사용 예시:
// CALL db.index.fulltext.queryNodes("entity_fulltext", "UR5e") 
// YIELD node, score
// RETURN node.name, node.description, score
// ORDER BY score DESC
// LIMIT 10;
