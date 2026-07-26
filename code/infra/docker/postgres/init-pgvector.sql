-- 互联网医疗中心平台 · PostgreSQL 初始化
-- 启用 pgvector 扩展（技术架构第5/7章：方案/案例向量检索、RAG 知识库）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
