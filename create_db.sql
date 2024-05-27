CREATE DATABASE textgpt
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Russian_Russia.1251'
    LC_CTYPE = 'Russian_Russia.1251'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

CREATE TABLE IF NOT EXISTS public.embeddings
(
    id bigint NOT NULL DEFAULT nextval('embeddings_id_seq'::regclass),
    content text COLLATE pg_catalog."default",
    embedding vector(256),
    name character varying COLLATE pg_catalog."default",
    CONSTRAINT embeddings_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.embeddings
    OWNER to postgres;

CREATE TABLE IF NOT EXISTS public.cash
(
    id bigint NOT NULL DEFAULT nextval('cash_id_seq'::regclass),
    question text COLLATE pg_catalog."default",
    anwser text COLLATE pg_catalog."default",
    embedding vector(256),
    mark integer DEFAULT 1,
    doc character varying(300) COLLATE pg_catalog."default",
    CONSTRAINT cash_pkey PRIMARY KEY (id),
    CONSTRAINT uniq_question UNIQUE (question)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.cash
    OWNER to postgres;