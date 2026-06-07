--
-- PostgreSQL database dump
--

\restrict ai8dL0oueShCyu4zYHfbwcG5Q8H2uAhlBZFvFZwtabDuQvhEESwZyaZv1l2sEcw

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: auditoria_saas; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.auditoria_saas (
    id bigint NOT NULL,
    tenant_id bigint,
    usuario_id bigint,
    accion character varying(200) NOT NULL,
    descripcion text,
    ip character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.auditoria_saas OWNER TO diagramador;

--
-- Name: auditoria_saas_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.auditoria_saas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.auditoria_saas_id_seq OWNER TO diagramador;

--
-- Name: auditoria_saas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.auditoria_saas_id_seq OWNED BY public.auditoria_saas.id;


--
-- Name: device_fcm_tokens; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.device_fcm_tokens (
    id bigint NOT NULL,
    tenant_id bigint,
    tenant_slug character varying(100),
    user_id bigint NOT NULL,
    role character varying(80) NOT NULL,
    sucursal_id bigint,
    fcm_token text NOT NULL,
    platform character varying(40) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone
);


ALTER TABLE public.device_fcm_tokens OWNER TO diagramador;

--
-- Name: device_fcm_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.device_fcm_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.device_fcm_tokens_id_seq OWNER TO diagramador;

--
-- Name: device_fcm_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.device_fcm_tokens_id_seq OWNED BY public.device_fcm_tokens.id;


--
-- Name: planes; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.planes (
    id bigint NOT NULL,
    nombre character varying(200) NOT NULL,
    descripcion text,
    precio_mensual numeric(12,2) DEFAULT 0 NOT NULL,
    limite_sucursales integer DEFAULT 1 NOT NULL,
    limite_tecnicos integer DEFAULT 10 NOT NULL,
    limite_administradores integer DEFAULT 2 NOT NULL,
    estado character varying(30) DEFAULT 'activo'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.planes OWNER TO diagramador;

--
-- Name: planes_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.planes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.planes_id_seq OWNER TO diagramador;

--
-- Name: planes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.planes_id_seq OWNED BY public.planes.id;


--
-- Name: saas_tenants; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.saas_tenants (
    id bigint NOT NULL,
    nombre character varying(200) NOT NULL,
    slug character varying(100) NOT NULL,
    razon_social character varying(300),
    nit character varying(50),
    correo character varying(200) NOT NULL,
    telefono character varying(50),
    direccion_principal text,
    zona character varying(120),
    ciudad character varying(120) DEFAULT 'Santa Cruz'::character varying NOT NULL,
    latitud double precision,
    longitud double precision,
    estado character varying(30) DEFAULT 'activo'::character varying NOT NULL,
    database_name character varying(200) NOT NULL,
    database_host character varying(200) DEFAULT 'db'::character varying NOT NULL,
    database_port integer DEFAULT 5432 NOT NULL,
    database_user character varying(200) NOT NULL,
    database_password character varying(500) NOT NULL,
    plan_id bigint,
    fecha_expiracion timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.saas_tenants OWNER TO diagramador;

--
-- Name: saas_tenants_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.saas_tenants_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.saas_tenants_id_seq OWNER TO diagramador;

--
-- Name: saas_tenants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.saas_tenants_id_seq OWNED BY public.saas_tenants.id;


--
-- Name: suscripciones; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.suscripciones (
    id bigint NOT NULL,
    tenant_id bigint NOT NULL,
    plan_id bigint NOT NULL,
    fecha_inicio timestamp with time zone DEFAULT now() NOT NULL,
    fecha_fin timestamp with time zone,
    estado character varying(30) DEFAULT 'activo'::character varying NOT NULL,
    monto numeric(12,2),
    metodo_pago character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.suscripciones OWNER TO diagramador;

--
-- Name: suscripciones_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.suscripciones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.suscripciones_id_seq OWNER TO diagramador;

--
-- Name: suscripciones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.suscripciones_id_seq OWNED BY public.suscripciones.id;


--
-- Name: auditoria_saas id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.auditoria_saas ALTER COLUMN id SET DEFAULT nextval('public.auditoria_saas_id_seq'::regclass);


--
-- Name: device_fcm_tokens id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.device_fcm_tokens ALTER COLUMN id SET DEFAULT nextval('public.device_fcm_tokens_id_seq'::regclass);


--
-- Name: planes id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.planes ALTER COLUMN id SET DEFAULT nextval('public.planes_id_seq'::regclass);


--
-- Name: saas_tenants id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.saas_tenants ALTER COLUMN id SET DEFAULT nextval('public.saas_tenants_id_seq'::regclass);


--
-- Name: suscripciones id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.suscripciones ALTER COLUMN id SET DEFAULT nextval('public.suscripciones_id_seq'::regclass);


--
-- Data for Name: auditoria_saas; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.auditoria_saas (id, tenant_id, usuario_id, accion, descripcion, ip, created_at) FROM stdin;
1	2	\N	TENANT_REGISTRADO	Empresa 'Auxilio Norte' registrada. Admin: carlos@auxilionorte.com	172.18.0.1	2026-06-06 13:08:42.857642+00
2	3	\N	TENANT_REGISTRADO	Empresa 'Taller Sur Premium' registrada. Admin: maria@tallersur.com	172.18.0.1	2026-06-06 13:14:13.957974+00
3	4	\N	TENANT_REGISTRADO	Empresa 'Taller Verificación Test' registrada. Admin: admin@tallertest.com	172.18.0.1	2026-06-06 13:17:33.16302+00
4	5	\N	TENANT_REGISTRADO	Empresa 'Tenant Bootstrap QA' registrada. Admin: admin.bootstrap.20260606@example.com. Sucursal principal: 1. Taller principal: 1	127.0.0.1	2026-06-06 14:41:54.188684+00
5	8	\N	TENANT_REGISTRADO	Empresa 'Smoke Tenant 1780768874' registrada. Admin: admin.smoke.1780768874@example.com. Sucursal principal: 1. Taller principal: 1	127.0.0.1	2026-06-06 18:01:14.828837+00
6	9	\N	TENANT_REGISTRADO	Empresa 'Smoke Demo A 1780794036' registrada. Admin: superadmin.a.1780794036@demo.bo. Sucursal principal: 1. Taller principal: 1	testclient	2026-06-07 01:00:37.029341+00
7	10	\N	TENANT_REGISTRADO	Empresa 'Smoke Demo B 1780794036' registrada. Admin: superadmin.b.1780794036@demo.bo. Sucursal principal: 1. Taller principal: 1	testclient	2026-06-07 01:00:37.619207+00
8	11	\N	TENANT_REGISTRADO	Empresa 'QA Integral 1780805933' registrada. Admin: qa.superadmin.1780805933@example.com. Sucursal principal: 1. Taller principal: 1	testclient	2026-06-07 04:18:53.945598+00
\.


--
-- Data for Name: device_fcm_tokens; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.device_fcm_tokens (id, tenant_id, tenant_slug, user_id, role, sucursal_id, fcm_token, platform, is_active, created_at, updated_at, last_seen_at) FROM stdin;
2	10	smoke_demo_b_1780794036	1	SUPERADMIN_TENANT	1	tenantB_token_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890	android	t	2026-06-07 01:12:01.700905+00	2026-06-07 01:12:46.618737+00	2026-06-07 01:12:46.618737+00
1	9	smoke_demo_a_1780794036	1	SUPERADMIN_TENANT	1	tenantA_token_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890	android	f	2026-06-07 01:12:01.629687+00	2026-06-07 01:12:46.743948+00	2026-06-07 01:12:46.544523+00
5	\N	\N	0	SUPERADMIN_GLOBAL	\N	global_token_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890	android	t	2026-06-07 01:13:13.164053+00	2026-06-07 01:13:13.164053+00	2026-06-07 01:13:13.164053+00
6	\N	\N	5	client	\N	eAMzGfSTQ5-AZ6S2BKwaIm:APA91bG2_LFfkt8rXv7mqJEm_7x7_33oNnKWJrLqONuatNpvrombmZn8upn3AbD8R288B-xvAAax2wLR_rNRzJfI72DKZOkAMKC66eQIDDN4nsEvKmkaJwA	android	t	2026-06-07 01:17:09.644022+00	2026-06-07 01:23:19.529923+00	2026-06-07 01:23:19.529923+00
15	10	smoke_demo_b_1780794036	2	ADMIN_SUCURSAL	1	tenantB_u2_token_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890	android	t	2026-06-07 01:28:23.94386+00	2026-06-07 01:28:23.94386+00	2026-06-07 01:28:23.94386+00
16	\N	\N	0	SUPERADMIN_GLOBAL	\N	global_u0_token_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890	android	t	2026-06-07 01:28:23.952544+00	2026-06-07 01:28:23.952544+00	2026-06-07 01:28:23.952544+00
14	9	smoke_demo_a_1780794036	2	ADMIN_SUCURSAL	1	tenantA_u2_token_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890	android	f	2026-06-07 01:28:23.875445+00	2026-06-07 01:28:24.034182+00	2026-06-07 01:28:23.875445+00
17	9	smoke_demo_a_1780794036	1	SUPERADMIN_TENANT	1	tenantqa_1780805933_abcdefghijkl	android	f	2026-06-07 04:18:55.310146+00	2026-06-07 04:18:55.324334+00	2026-06-07 04:18:55.310146+00
\.


--
-- Data for Name: planes; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.planes (id, nombre, descripcion, precio_mensual, limite_sucursales, limite_tecnicos, limite_administradores, estado, created_at) FROM stdin;
1	Básico	Plan inicial para talleres pequeños	0.00	1	5	1	activo	2026-06-06 12:58:44.808922+00
2	Estándar	Plan para talleres con varias sucursales	199.00	3	20	3	activo	2026-06-06 12:58:44.808922+00
3	Premium	Plan completo para redes de talleres	499.00	10	100	10	activo	2026-06-06 12:58:44.808922+00
\.


--
-- Data for Name: saas_tenants; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.saas_tenants (id, nombre, slug, razon_social, nit, correo, telefono, direccion_principal, zona, ciudad, latitud, longitud, estado, database_name, database_host, database_port, database_user, database_password, plan_id, fecha_expiracion, created_at, updated_at) FROM stdin;
1	Mecánicos Express	mecanicos_express	\N	\N	admin@mecanicosexpress.com	76543210	Av. Banzer Km 5	Zona Norte	Santa Cruz	-17.78	-63.18	activo	tenant_mecanicos_express	db	5432	diagramador	diagramador	2	\N	2026-06-06 13:07:41.887951+00	2026-06-06 13:07:41.887951+00
2	Auxilio Norte	auxilio_norte	Auxilio Norte S.R.L.	12345678	contacto@auxilionorte.com	75000001	Av. Radial 27	Zona Norte	Santa Cruz	-17.72	-63.14	activo	tenant_auxilio_norte	db	5432	diagramador	diagramador	1	\N	2026-06-06 13:08:42.591254+00	2026-06-06 13:08:42.591254+00
3	Taller Sur Premium	taller_sur_premium	\N	\N	info@tallersur.com	\N	\N	\N	Cochabamba	\N	\N	activo	tenant_taller_sur_premium	db	5432	diagramador	diagramador	3	\N	2026-06-06 13:14:13.675182+00	2026-06-06 13:14:13.675182+00
5	Tenant Bootstrap QA	tenant_bootstrap_qa	Tenant Bootstrap QA S.R.L.	QA-20260606	qa.bootstrap.20260606@example.com	76543210	Av. SaaS 123	Norte	Santa Cruz	-17.77	-63.18	activo	tenant_tenant_bootstrap_qa	db	5432	diagramador	diagramador	1	\N	2026-06-06 14:41:53.882186+00	2026-06-06 14:41:53.882186+00
4	Taller Verificación Test	taller_verificacion_test	\N	\N	test.verify@tallertest.com	\N	\N	\N	Santa Cruz	\N	\N	activo	tenant_taller_verificacion_test	db	5432	diagramador	diagramador	1	\N	2026-06-06 13:17:32.900273+00	2026-06-06 15:12:24.723147+00
8	Smoke Tenant 1780768874	smoke_tenant_1780768874	Smoke Tenant 1780768874 SRL	900768874	smoke.tenant.1780768874@example.com	70000001	Av. Prueba 123	Centro	Santa Cruz	-17.7833	-63.1821	activo	tenant_smoke_tenant_1780768874	db	5432	diagramador	diagramador	\N	\N	2026-06-06 18:01:14.486552+00	2026-06-06 18:01:14.486552+00
9	Smoke Demo A 1780794036	smoke_demo_a_1780794036	Smoke Demo A SRL 1780794036	900794036	smoke.empresa.a.1780794036@demo.bo	70010001	Av. Demo 123	Norte	Santa Cruz	-17.7833	-63.1821	activo	tenant_smoke_demo_a_1780794036	db	5432	diagramador	diagramador	1	\N	2026-06-07 01:00:36.627448+00	2026-06-07 01:00:36.627448+00
10	Smoke Demo B 1780794036	smoke_demo_b_1780794036	Smoke Demo B SRL 1780794036	901794036	smoke.empresa.b.1780794036@demo.bo	70010002	Av. Demo 456	Sur	Santa Cruz	-17.82	-63.15	activo	tenant_smoke_demo_b_1780794036	db	5432	diagramador	diagramador	1	\N	2026-06-07 01:00:37.234136+00	2026-06-07 01:00:37.234136+00
11	QA Integral 1780805933	qa_integral_1780805933	QA Integral 1780805933 SRL	NIT-1780805933	qa.empresa.1780805933@example.com	70000001	Av QA 123	zona norte	Santa Cruz	\N	\N	activo	tenant_qa_integral_1780805933	db	5432	diagramador	diagramador	1	\N	2026-06-07 04:18:53.620085+00	2026-06-07 04:18:53.620085+00
\.


--
-- Data for Name: suscripciones; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.suscripciones (id, tenant_id, plan_id, fecha_inicio, fecha_fin, estado, monto, metodo_pago, created_at) FROM stdin;
1	5	1	2026-06-06 14:41:54.181223+00	\N	activo	0.00	registro_inicial	2026-06-06 14:41:54.181223+00
2	8	1	2026-06-06 18:01:14.824766+00	\N	activo	0.00	registro_inicial	2026-06-06 18:01:14.824766+00
3	9	1	2026-06-07 01:00:37.02372+00	\N	activo	0.00	registro_inicial	2026-06-07 01:00:37.02372+00
4	10	1	2026-06-07 01:00:37.615575+00	\N	activo	0.00	registro_inicial	2026-06-07 01:00:37.615575+00
5	11	1	2026-06-07 04:18:53.941388+00	\N	activo	0.00	registro_inicial	2026-06-07 04:18:53.941388+00
\.


--
-- Name: auditoria_saas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.auditoria_saas_id_seq', 8, true);


--
-- Name: device_fcm_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.device_fcm_tokens_id_seq', 17, true);


--
-- Name: planes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.planes_id_seq', 3, true);


--
-- Name: saas_tenants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.saas_tenants_id_seq', 11, true);


--
-- Name: suscripciones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.suscripciones_id_seq', 5, true);


--
-- Name: auditoria_saas auditoria_saas_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.auditoria_saas
    ADD CONSTRAINT auditoria_saas_pkey PRIMARY KEY (id);


--
-- Name: device_fcm_tokens device_fcm_tokens_fcm_token_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.device_fcm_tokens
    ADD CONSTRAINT device_fcm_tokens_fcm_token_key UNIQUE (fcm_token);


--
-- Name: device_fcm_tokens device_fcm_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.device_fcm_tokens
    ADD CONSTRAINT device_fcm_tokens_pkey PRIMARY KEY (id);


--
-- Name: planes planes_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.planes
    ADD CONSTRAINT planes_pkey PRIMARY KEY (id);


--
-- Name: saas_tenants saas_tenants_correo_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.saas_tenants
    ADD CONSTRAINT saas_tenants_correo_key UNIQUE (correo);


--
-- Name: saas_tenants saas_tenants_database_name_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.saas_tenants
    ADD CONSTRAINT saas_tenants_database_name_key UNIQUE (database_name);


--
-- Name: saas_tenants saas_tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.saas_tenants
    ADD CONSTRAINT saas_tenants_pkey PRIMARY KEY (id);


--
-- Name: saas_tenants saas_tenants_slug_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.saas_tenants
    ADD CONSTRAINT saas_tenants_slug_key UNIQUE (slug);


--
-- Name: suscripciones suscripciones_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.suscripciones
    ADD CONSTRAINT suscripciones_pkey PRIMARY KEY (id);


--
-- Name: idx_device_fcm_tokens_slug_user_active; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_device_fcm_tokens_slug_user_active ON public.device_fcm_tokens USING btree (tenant_slug, user_id, role, is_active);


--
-- Name: idx_device_fcm_tokens_user_role_active; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_device_fcm_tokens_user_role_active ON public.device_fcm_tokens USING btree (user_id, role, is_active);


--
-- Name: idx_device_fcm_tokens_user_tenant_active; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_device_fcm_tokens_user_tenant_active ON public.device_fcm_tokens USING btree (user_id, tenant_id, role, is_active);


--
-- Name: auditoria_saas auditoria_saas_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.auditoria_saas
    ADD CONSTRAINT auditoria_saas_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.saas_tenants(id) ON DELETE SET NULL;


--
-- Name: device_fcm_tokens device_fcm_tokens_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.device_fcm_tokens
    ADD CONSTRAINT device_fcm_tokens_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.saas_tenants(id) ON DELETE SET NULL;


--
-- Name: saas_tenants saas_tenants_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.saas_tenants
    ADD CONSTRAINT saas_tenants_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.planes(id) ON DELETE SET NULL;


--
-- Name: suscripciones suscripciones_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.suscripciones
    ADD CONSTRAINT suscripciones_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.planes(id) ON DELETE RESTRICT;


--
-- Name: suscripciones suscripciones_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.suscripciones
    ADD CONSTRAINT suscripciones_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.saas_tenants(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ai8dL0oueShCyu4zYHfbwcG5Q8H2uAhlBZFvFZwtabDuQvhEESwZyaZv1l2sEcw

