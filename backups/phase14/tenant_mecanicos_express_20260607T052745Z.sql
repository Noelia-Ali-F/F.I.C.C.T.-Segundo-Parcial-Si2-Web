--
-- PostgreSQL database dump
--

\restrict bhYAuGpA1gyTZznmVtdGdF0deL9poUaTVMuqO239C30wEOl9WtWGv75kPmKYksx

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
-- Name: clients; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.clients (
    id bigint NOT NULL,
    identity_card character varying(40) NOT NULL,
    full_name character varying(160) NOT NULL,
    email character varying(160) NOT NULL,
    phone character varying(40) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(40) DEFAULT 'CLIENTE'::character varying NOT NULL,
    status character varying(30) DEFAULT 'active'::character varying NOT NULL,
    accepted_terms boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.clients OWNER TO diagramador;

--
-- Name: clients_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.clients_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clients_id_seq OWNER TO diagramador;

--
-- Name: clients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.clients_id_seq OWNED BY public.clients.id;


--
-- Name: device_fcm_tokens; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.device_fcm_tokens (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    fcm_token text NOT NULL,
    platform character varying(40) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
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
-- Name: emergency_assignments; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.emergency_assignments (
    id bigint NOT NULL,
    emergency_report_id bigint NOT NULL,
    workshop_id bigint NOT NULL,
    technician_id bigint NOT NULL,
    assignment_status character varying(30) DEFAULT 'asignado'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.emergency_assignments OWNER TO diagramador;

--
-- Name: emergency_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.emergency_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.emergency_assignments_id_seq OWNER TO diagramador;

--
-- Name: emergency_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.emergency_assignments_id_seq OWNED BY public.emergency_assignments.id;


--
-- Name: emergency_reports; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.emergency_reports (
    id bigint NOT NULL,
    local_id character varying(64),
    client_id bigint,
    vehicle_name character varying(160) NOT NULL,
    vehicle_plate character varying(40) NOT NULL,
    problem_type character varying(120) NOT NULL,
    price integer,
    emergency_status character varying(30) DEFAULT 'pendiente'::character varying NOT NULL,
    problem_type_standardized character varying(120),
    photo_problem_type_standardized character varying(120),
    photo_classification_confidence double precision,
    photo_classification_error text,
    description text,
    latitude double precision,
    longitude double precision,
    address character varying(255),
    zone character varying(120),
    nearest_workshop_id bigint,
    nearest_workshop_name character varying(160),
    nearest_workshop_specialty character varying(120),
    nearest_workshop_zone character varying(120),
    nearest_workshop_distance_meters double precision,
    audio_duration_seconds double precision,
    audio_transcript text,
    audio_transcript_status character varying(30),
    audio_transcript_error text,
    photo_paths text DEFAULT '[]'::text NOT NULL,
    photo_urls text DEFAULT '[]'::text NOT NULL,
    audio_path character varying(255),
    audio_url character varying(255),
    rejection_reason text,
    rejected_at timestamp with time zone,
    hora_llegada timestamp with time zone,
    latitud_llegada double precision,
    longitud_llegada double precision,
    sucursal_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.emergency_reports OWNER TO diagramador;

--
-- Name: emergency_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.emergency_reports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.emergency_reports_id_seq OWNER TO diagramador;

--
-- Name: emergency_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.emergency_reports_id_seq OWNED BY public.emergency_reports.id;


--
-- Name: emergency_status_history; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.emergency_status_history (
    id bigint NOT NULL,
    emergency_id bigint NOT NULL,
    previous_status character varying(50),
    new_status character varying(50) NOT NULL,
    changed_by_role character varying(50),
    changed_by_user_id bigint,
    observation text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.emergency_status_history OWNER TO diagramador;

--
-- Name: emergency_status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.emergency_status_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.emergency_status_history_id_seq OWNER TO diagramador;

--
-- Name: emergency_status_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.emergency_status_history_id_seq OWNED BY public.emergency_status_history.id;


--
-- Name: emergency_tracking_points; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.emergency_tracking_points (
    id bigint NOT NULL,
    emergency_id bigint NOT NULL,
    technician_id bigint,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    source character varying(50) DEFAULT 'system'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.emergency_tracking_points OWNER TO diagramador;

--
-- Name: emergency_tracking_points_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.emergency_tracking_points_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.emergency_tracking_points_id_seq OWNER TO diagramador;

--
-- Name: emergency_tracking_points_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.emergency_tracking_points_id_seq OWNED BY public.emergency_tracking_points.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.notifications (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    title character varying(160) NOT NULL,
    message text NOT NULL,
    is_read boolean DEFAULT false NOT NULL,
    payload_json text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.notifications OWNER TO diagramador;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.notifications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO diagramador;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: quotation_offers; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.quotation_offers (
    id bigint NOT NULL,
    quotation_request_id bigint NOT NULL,
    workshop_id bigint NOT NULL,
    workshop_rating double precision,
    price numeric(12,2),
    service_description text,
    spare_parts text,
    labor_detail text,
    labor_cost numeric(12,2),
    spare_parts_cost numeric(12,2),
    estimated_service_time character varying(80),
    offer_status character varying(30) DEFAULT 'pendiente'::character varying NOT NULL,
    submitted_at timestamp with time zone,
    selected_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    estimated_arrival_time character varying(80),
    warranty character varying(255),
    validity_days integer,
    observations text,
    condiciones_servicio text,
    status character varying(30) DEFAULT 'enviada'::character varying NOT NULL,
    expires_at timestamp with time zone
);


ALTER TABLE public.quotation_offers OWNER TO diagramador;

--
-- Name: quotation_offers_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.quotation_offers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quotation_offers_id_seq OWNER TO diagramador;

--
-- Name: quotation_offers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.quotation_offers_id_seq OWNED BY public.quotation_offers.id;


--
-- Name: quotation_request_history; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.quotation_request_history (
    id bigint NOT NULL,
    quotation_request_id bigint NOT NULL,
    event_type character varying(50) NOT NULL,
    detail text,
    actor_role character varying(50),
    actor_user_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.quotation_request_history OWNER TO diagramador;

--
-- Name: quotation_request_history_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.quotation_request_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quotation_request_history_id_seq OWNER TO diagramador;

--
-- Name: quotation_request_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.quotation_request_history_id_seq OWNED BY public.quotation_request_history.id;


--
-- Name: quotation_request_workshops; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.quotation_request_workshops (
    id bigint NOT NULL,
    quotation_request_id bigint NOT NULL,
    workshop_id bigint NOT NULL,
    status character varying(30) DEFAULT 'notificado'::character varying NOT NULL,
    notified_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.quotation_request_workshops OWNER TO diagramador;

--
-- Name: quotation_request_workshops_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.quotation_request_workshops_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quotation_request_workshops_id_seq OWNER TO diagramador;

--
-- Name: quotation_request_workshops_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.quotation_request_workshops_id_seq OWNED BY public.quotation_request_workshops.id;


--
-- Name: quotation_requests; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.quotation_requests (
    id bigint NOT NULL,
    emergency_id bigint,
    client_id bigint,
    status character varying(30) DEFAULT 'abierto'::character varying NOT NULL,
    requested_workshops_count integer DEFAULT 0 NOT NULL,
    received_offers_count integer DEFAULT 0 NOT NULL,
    selected_offer_id bigint,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.quotation_requests OWNER TO diagramador;

--
-- Name: quotation_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.quotation_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quotation_requests_id_seq OWNER TO diagramador;

--
-- Name: quotation_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.quotation_requests_id_seq OWNED BY public.quotation_requests.id;


--
-- Name: sucursales; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.sucursales (
    id bigint NOT NULL,
    nombre character varying(200) NOT NULL,
    direccion text DEFAULT ''::text NOT NULL,
    zona character varying(120),
    ciudad character varying(120) DEFAULT 'Santa Cruz'::character varying NOT NULL,
    latitud double precision,
    longitud double precision,
    telefono character varying(50),
    responsable character varying(160),
    estado character varying(30) DEFAULT 'activo'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.sucursales OWNER TO diagramador;

--
-- Name: sucursales_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.sucursales_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sucursales_id_seq OWNER TO diagramador;

--
-- Name: sucursales_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.sucursales_id_seq OWNED BY public.sucursales.id;


--
-- Name: technicians; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.technicians (
    id bigint NOT NULL,
    workshop_id bigint,
    full_name character varying(160) NOT NULL,
    phone character varying(40) NOT NULL,
    email character varying(160) DEFAULT ''::character varying NOT NULL,
    specialty character varying(120) NOT NULL,
    status character varying(30) NOT NULL,
    sucursal_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.technicians OWNER TO diagramador;

--
-- Name: technicians_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.technicians_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.technicians_id_seq OWNER TO diagramador;

--
-- Name: technicians_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.technicians_id_seq OWNED BY public.technicians.id;


--
-- Name: usuarios_tenant; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.usuarios_tenant (
    id bigint NOT NULL,
    email character varying(160) NOT NULL,
    full_name character varying(160) NOT NULL,
    phone character varying(40) DEFAULT ''::character varying NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(60) DEFAULT 'TECNICO'::character varying NOT NULL,
    sucursal_id bigint,
    estado character varying(30) DEFAULT 'activo'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.usuarios_tenant OWNER TO diagramador;

--
-- Name: usuarios_tenant_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.usuarios_tenant_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usuarios_tenant_id_seq OWNER TO diagramador;

--
-- Name: usuarios_tenant_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.usuarios_tenant_id_seq OWNED BY public.usuarios_tenant.id;


--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.vehicles (
    id bigint NOT NULL,
    client_id bigint,
    brand character varying(120) NOT NULL,
    model character varying(120) NOT NULL,
    year integer NOT NULL,
    plate character varying(40) NOT NULL,
    color character varying(80) NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    photo_path character varying(255),
    photo_url character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.vehicles OWNER TO diagramador;

--
-- Name: vehicles_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.vehicles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicles_id_seq OWNER TO diagramador;

--
-- Name: vehicles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.vehicles_id_seq OWNED BY public.vehicles.id;


--
-- Name: workshop_registrations; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.workshop_registrations (
    id bigint NOT NULL,
    workshop_name character varying(160) NOT NULL,
    contact_name character varying(160) NOT NULL,
    phone character varying(40) NOT NULL,
    email character varying(160) NOT NULL,
    zone character varying(120) NOT NULL,
    specialty character varying(120) NOT NULL,
    approval_status character varying(30) DEFAULT 'pendiente'::character varying NOT NULL,
    availability_status character varying(30) DEFAULT 'disponible'::character varying NOT NULL,
    password_hash character varying(255),
    latitude double precision,
    longitude double precision,
    timezone character varying(120),
    utc_offset_minutes integer,
    sucursal_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.workshop_registrations OWNER TO diagramador;

--
-- Name: workshop_registrations_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.workshop_registrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workshop_registrations_id_seq OWNER TO diagramador;

--
-- Name: workshop_registrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.workshop_registrations_id_seq OWNED BY public.workshop_registrations.id;


--
-- Name: clients id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.clients ALTER COLUMN id SET DEFAULT nextval('public.clients_id_seq'::regclass);


--
-- Name: device_fcm_tokens id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.device_fcm_tokens ALTER COLUMN id SET DEFAULT nextval('public.device_fcm_tokens_id_seq'::regclass);


--
-- Name: emergency_assignments id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_assignments ALTER COLUMN id SET DEFAULT nextval('public.emergency_assignments_id_seq'::regclass);


--
-- Name: emergency_reports id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_reports ALTER COLUMN id SET DEFAULT nextval('public.emergency_reports_id_seq'::regclass);


--
-- Name: emergency_status_history id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_status_history ALTER COLUMN id SET DEFAULT nextval('public.emergency_status_history_id_seq'::regclass);


--
-- Name: emergency_tracking_points id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_tracking_points ALTER COLUMN id SET DEFAULT nextval('public.emergency_tracking_points_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: quotation_offers id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_offers ALTER COLUMN id SET DEFAULT nextval('public.quotation_offers_id_seq'::regclass);


--
-- Name: quotation_request_history id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_request_history ALTER COLUMN id SET DEFAULT nextval('public.quotation_request_history_id_seq'::regclass);


--
-- Name: quotation_request_workshops id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_request_workshops ALTER COLUMN id SET DEFAULT nextval('public.quotation_request_workshops_id_seq'::regclass);


--
-- Name: quotation_requests id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_requests ALTER COLUMN id SET DEFAULT nextval('public.quotation_requests_id_seq'::regclass);


--
-- Name: sucursales id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.sucursales ALTER COLUMN id SET DEFAULT nextval('public.sucursales_id_seq'::regclass);


--
-- Name: technicians id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.technicians ALTER COLUMN id SET DEFAULT nextval('public.technicians_id_seq'::regclass);


--
-- Name: usuarios_tenant id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.usuarios_tenant ALTER COLUMN id SET DEFAULT nextval('public.usuarios_tenant_id_seq'::regclass);


--
-- Name: vehicles id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.vehicles ALTER COLUMN id SET DEFAULT nextval('public.vehicles_id_seq'::regclass);


--
-- Name: workshop_registrations id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.workshop_registrations ALTER COLUMN id SET DEFAULT nextval('public.workshop_registrations_id_seq'::regclass);


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.clients (id, identity_card, full_name, email, phone, password_hash, role, status, accepted_terms, created_at, updated_at) FROM stdin;
9001	CI9001	Cliente A Tenant	clientea_tenant_test@emergencias.bo	7009001	test	CLIENTE	active	t	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
9002	CI9002	Cliente B Tenant	clienteb_tenant_test@emergencias.bo	7009002	test	CLIENTE	active	t	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
97001	CI97001	Cliente Owner	cliente.owner.mecanicos_express@test.local	72010001	x	client	active	t	2026-06-07 02:02:28.384263+00	2026-06-07 02:02:28.384263+00
97002	CI97002	Cliente Other	cliente.other.mecanicos_express@test.local	72010002	x	client	active	t	2026-06-07 02:02:28.384263+00	2026-06-07 02:02:28.384263+00
\.


--
-- Data for Name: device_fcm_tokens; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.device_fcm_tokens (id, user_id, fcm_token, platform, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: emergency_assignments; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_assignments (id, emergency_report_id, workshop_id, technician_id, assignment_status, created_at, updated_at) FROM stdin;
9401	9301	9101	9201	asignado	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
9402	9302	9102	9202	asignado	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
1	1	97201	97101	asignado	2026-06-07 02:02:33.091047+00	2026-06-07 02:02:33.091047+00
97401	97401	97201	97101	asignado	2026-06-07 02:27:01.945305+00	2026-06-07 02:27:01.945305+00
\.


--
-- Data for Name: emergency_reports; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_reports (id, local_id, client_id, vehicle_name, vehicle_plate, problem_type, price, emergency_status, problem_type_standardized, photo_problem_type_standardized, photo_classification_confidence, photo_classification_error, description, latitude, longitude, address, zone, nearest_workshop_id, nearest_workshop_name, nearest_workshop_specialty, nearest_workshop_zone, nearest_workshop_distance_meters, audio_duration_seconds, audio_transcript, audio_transcript_status, audio_transcript_error, photo_paths, photo_urls, audio_path, audio_url, rejection_reason, rejected_at, hora_llegada, latitud_llegada, longitud_llegada, sucursal_id, created_at, updated_at) FROM stdin;
9301	fase8-a	9001	Auto A	A-9001	Motor	100	auxilio_asignado	\N	\N	\N	\N	Emergencia A	-17.78	-63.18	Direccion A	Norte	9101	Workshop Norte	Motor	Norte	150	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	77	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
9302	fase8-b	9002	Auto B	B-9002	Batería	80	auxilio_asignado	\N	\N	\N	\N	Emergencia B	-17.82	-63.15	Direccion B	Sur	9102	Workshop Sur	Batería	Sur	120	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	88	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
1	ws-phase11-2-a	97001	Auto WS	WS-1122	Motor	100	auxilio_en_camino	Motor	\N	\N	\N	Prueba websocket emergencia	-17.78	-63.182	Av test 123	zona norte	97201	WS Norte	Motor	zona norte	150	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	77	2026-06-07 02:02:28.765305+00	2026-06-07 02:02:35.57663+00
2	ws-phase11-2-r	97001	Auto WS Reject	WS-1133	Motor	100	en_revision	Motor	\N	\N	\N	Prueba websocket rechazo	-17.78	-63.182	Av test 124	zona norte	9101	Workshop Norte	Motor	Norte	367.0959905719692	\N	\N	\N	\N	[]	[]	\N	\N	Prueba rechazo ws	2026-06-07 02:02:42.680933+00	\N	\N	\N	77	2026-06-07 02:02:40.554681+00	2026-06-07 02:02:42.681604+00
3	ws-assign-focus	97001	Auto Assign	WS-AF1	Motor	100	activo	Motor	\N	\N	\N	focus assign	-17.78	-63.182	Av test 125	zona norte	97201	WS Norte	Motor	zona norte	150	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	77	2026-06-07 02:05:24.979618+00	2026-06-07 02:05:24.998641+00
4	ws-track-owner-only	97001	Auto Track2	WS-T22	Motor	100	activo	Motor	\N	\N	\N	focus tracking 2	-17.78	-63.182	Av test 128	zona norte	97201	WS Norte	Motor	zona norte	150	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	77	2026-06-07 02:07:26.115452+00	2026-06-07 02:07:26.136439+00
5	ws-reject-owner-only	97001	Auto Reject2	WS-R22	Motor	100	en_revision	Motor	\N	\N	\N	focus reject 2	-17.78	-63.182	Av test 129	zona norte	9101	Workshop Norte	Motor	Norte	367.0959905719692	\N	\N	\N	\N	[]	[]	\N	\N	Prueba rechazo ws	2026-06-07 02:07:28.290236+00	\N	\N	\N	77	2026-06-07 02:07:28.265004+00	2026-06-07 02:07:28.290843+00
97401	ws-manual-track-final	97001	Auto Manual Track	WS-MTRK	Motor	100	auxilio_en_camino	Motor	\N	\N	\N	Emergencia manual para validar tracking websocket	-17.78	-63.182	Av test 131	zona norte	97201	WS Norte	Motor	zona norte	150	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	77	2026-06-07 02:27:01.945305+00	2026-06-07 02:27:01.945305+00
\.


--
-- Data for Name: emergency_status_history; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_status_history (id, emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation, created_at) FROM stdin;
1	1	\N	solicitud_recibida	client	97001	\N	2026-06-07 02:02:28.765305+00
2	1	pendiente	activo	workshop	97201	\N	2026-06-07 02:02:30.894772+00
3	1	activo	auxilio_en_camino	workshop	97201	\N	2026-06-07 02:02:35.57663+00
4	2	\N	solicitud_recibida	client	97001	\N	2026-06-07 02:02:40.554681+00
5	2	pendiente	solicitud_cancelada	admin_sucursal	99001	Prueba rechazo ws	2026-06-07 02:02:42.681604+00
6	2	solicitud_cancelada	en_revision	admin_sucursal	99001	Solicitud reasignada automaticamente al taller Workshop Norte	2026-06-07 02:02:42.693614+00
7	3	\N	solicitud_recibida	client	97001	\N	2026-06-07 02:05:24.979618+00
8	3	pendiente	activo	workshop	97201	\N	2026-06-07 02:05:24.998641+00
9	4	\N	solicitud_recibida	client	97001	\N	2026-06-07 02:07:26.115452+00
10	4	pendiente	activo	workshop	97201	\N	2026-06-07 02:07:26.136439+00
11	5	\N	solicitud_recibida	client	97001	\N	2026-06-07 02:07:28.265004+00
12	5	pendiente	solicitud_cancelada	admin_sucursal	99001	Prueba rechazo ws	2026-06-07 02:07:28.290843+00
13	5	solicitud_cancelada	en_revision	admin_sucursal	99001	Solicitud reasignada automaticamente al taller Workshop Norte	2026-06-07 02:07:28.30312+00
14	97401	activo	auxilio_en_camino	admin_sucursal	99001	Seed manual para tracking websocket	2026-06-07 02:27:01.945305+00
\.


--
-- Data for Name: emergency_tracking_points; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_tracking_points (id, emergency_id, technician_id, latitude, longitude, source, created_at) FROM stdin;
1	1	97101	-17.781	-63.183	gps	2026-06-07 02:02:38.071886+00
2	97401	97101	-17.7833	-63.1821	technician_app	2026-06-07 02:28:49.037036+00
3	97401	97101	-17.7833	-63.1821	technician_app	2026-06-07 02:54:36.058317+00
4	97401	97101	-17.78331	-63.18211	technician_app	2026-06-07 02:54:42.556257+00
5	97401	97101	-17.7833	-63.1821	technician_app	2026-06-07 02:55:20.942747+00
6	97401	97101	-17.78331	-63.18211	technician_app	2026-06-07 02:55:27.349106+00
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.notifications (id, user_id, title, message, is_read, payload_json, created_at) FROM stdin;
1	97001	Emergencia aceptada	WS Norte acepto tu emergencia: Prueba websocket emergencia	f	{"type": "emergency_accepted", "emergency_id": "1", "workshop_id": "97201", "workshop_name": "WS Norte", "incident_description": "Prueba websocket emergencia"}	2026-06-07 02:02:30.902754+00
2	97001	Tecnico asignado	Tecnico Norte de WS Norte atendera: Prueba websocket emergencia	f	{"type": "technician_assigned", "emergency_id": "1", "workshop_id": "97201", "technician_id": "97101", "workshop_name": "WS Norte", "technician_name": "Tecnico Norte", "incident_description": "Prueba websocket emergencia", "technician_latitude": "-17.77", "technician_longitude": "-63.18"}	2026-06-07 02:02:33.10028+00
3	97001	Estado actualizado	Tu solicitud ahora está: Auxilio en camino	f	{"type": "emergency_status_updated", "emergency_id": "1", "status": "auxilio_en_camino", "status_label": "Auxilio en camino"}	2026-06-07 02:02:35.583703+00
4	97001	Solicitud reasignada	Tu solicitud fue enviada a otro taller disponible	f	{"type": "emergency_reassigned", "emergency_id": "2", "status": "en_revision", "status_label": "En revisión", "new_workshop_id": "9101", "new_workshop_name": "Workshop Norte", "message": "Tu solicitud fue enviada a otro taller disponible"}	2026-06-07 02:02:42.699505+00
5	97001	Emergencia aceptada	WS Norte acepto tu emergencia: focus assign	f	{"type": "emergency_accepted", "emergency_id": "3", "workshop_id": "97201", "workshop_name": "WS Norte", "incident_description": "focus assign"}	2026-06-07 02:05:25.006133+00
6	97001	Emergencia aceptada	WS Norte acepto tu emergencia: focus tracking 2	f	{"type": "emergency_accepted", "emergency_id": "4", "workshop_id": "97201", "workshop_name": "WS Norte", "incident_description": "focus tracking 2"}	2026-06-07 02:07:26.144957+00
7	97001	Solicitud reasignada	Tu solicitud fue enviada a otro taller disponible	f	{"type": "emergency_reassigned", "emergency_id": "5", "status": "en_revision", "status_label": "En revisión", "new_workshop_id": "9101", "new_workshop_name": "Workshop Norte", "message": "Tu solicitud fue enviada a otro taller disponible"}	2026-06-07 02:07:28.308754+00
\.


--
-- Data for Name: quotation_offers; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_offers (id, quotation_request_id, workshop_id, workshop_rating, price, service_description, spare_parts, labor_detail, labor_cost, spare_parts_cost, estimated_service_time, offer_status, submitted_at, selected_at, created_at, updated_at, estimated_arrival_time, warranty, validity_days, observations, condiciones_servicio, status, expires_at) FROM stdin;
\.


--
-- Data for Name: quotation_request_history; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_request_history (id, quotation_request_id, event_type, detail, actor_role, actor_user_id, created_at) FROM stdin;
\.


--
-- Data for Name: quotation_request_workshops; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_request_workshops (id, quotation_request_id, workshop_id, status, notified_at, created_at) FROM stdin;
\.


--
-- Data for Name: quotation_requests; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_requests (id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sucursales; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.sucursales (id, nombre, direccion, zona, ciudad, latitud, longitud, telefono, responsable, estado, created_at, updated_at) FROM stdin;
77	Sucursal Norte	Direccion Norte	Norte	Santa Cruz	-17.7833	-63.1821	7300077	Admin Norte	activo	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
88	Sucursal Sur	Direccion Sur	Sur	Santa Cruz	-17.82	-63.15	7300088	Admin Sur	activo	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
\.


--
-- Data for Name: technicians; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.technicians (id, workshop_id, full_name, phone, email, specialty, status, sucursal_id, created_at, updated_at) FROM stdin;
9201	9101	Tecnico Norte	7209201	tecnico.norte@test.bo	Motor	disponible	77	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
9202	9102	Tecnico Sur	7209202	tecnico.sur@test.bo	Batería	disponible	88	2026-06-07 00:49:54.371339+00	2026-06-07 00:49:54.371339+00
97102	97202	Tecnico Sur	71010002	tec.sur.mecanicos_express@test.local	Motor	disponible	88	2026-06-07 02:02:28.384263+00	2026-06-07 02:02:28.384263+00
97101	97201	Tecnico Norte	71010001	tec.norte.mecanicos_express@test.local	Motor	ocupado	77	2026-06-07 02:02:28.384263+00	2026-06-07 02:02:33.091047+00
\.


--
-- Data for Name: usuarios_tenant; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.usuarios_tenant (id, email, full_name, phone, password_hash, role, sucursal_id, estado, created_at, updated_at) FROM stdin;
1	admin@mecanicosexpress.com	Administrador Mecánicos Express	76543210	8ad4cedd8dd8c64226be5519a7915bd0$a79210b53b5e643dd5c12e7d0c49565cb119c3729895f134aadd522e23ce75bd	SUPERADMIN_TENANT	\N	activo	2026-06-06 13:07:57.70402+00	2026-06-06 13:07:57.70402+00
\.


--
-- Data for Name: vehicles; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.vehicles (id, client_id, brand, model, year, plate, color, is_primary, photo_path, photo_url, created_at) FROM stdin;
\.


--
-- Data for Name: workshop_registrations; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.workshop_registrations (id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at) FROM stdin;
9101	Workshop Norte	Admin Norte	7109101	norte@workshop.test	Norte	Motor	activo	disponible	\N	-17.7833	-63.1821	\N	\N	77	2026-06-07 00:49:54.371339+00
9102	Workshop Sur	Admin Sur	7109102	sur@workshop.test	Sur	Batería	activo	disponible	\N	-17.82	-63.15	\N	\N	88	2026-06-07 00:49:54.371339+00
97201	WS Norte	Contacto Norte	70010001	ws.norte.mecanicos_express@test.local	zona norte	Motor	activo	disponible	x	-17.77	-63.18	UTC	0	77	2026-06-07 02:02:28.384263+00
97202	WS Sur	Contacto Sur	70010002	ws.sur.mecanicos_express@test.local	zona sur	Motor	activo	disponible	x	-17.81	-63.2	UTC	0	88	2026-06-07 02:02:28.384263+00
\.


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.clients_id_seq', 1, false);


--
-- Name: device_fcm_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.device_fcm_tokens_id_seq', 1, false);


--
-- Name: emergency_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_assignments_id_seq', 1, true);


--
-- Name: emergency_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_reports_id_seq', 5, true);


--
-- Name: emergency_status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_status_history_id_seq', 14, true);


--
-- Name: emergency_tracking_points_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_tracking_points_id_seq', 6, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.notifications_id_seq', 7, true);


--
-- Name: quotation_offers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_offers_id_seq', 1, false);


--
-- Name: quotation_request_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_request_history_id_seq', 1, false);


--
-- Name: quotation_request_workshops_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_request_workshops_id_seq', 1, false);


--
-- Name: quotation_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_requests_id_seq', 1, false);


--
-- Name: sucursales_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.sucursales_id_seq', 1, false);


--
-- Name: technicians_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.technicians_id_seq', 1, false);


--
-- Name: usuarios_tenant_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.usuarios_tenant_id_seq', 1, true);


--
-- Name: vehicles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.vehicles_id_seq', 1, false);


--
-- Name: workshop_registrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.workshop_registrations_id_seq', 1, false);


--
-- Name: clients clients_email_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_email_key UNIQUE (email);


--
-- Name: clients clients_identity_card_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_identity_card_key UNIQUE (identity_card);


--
-- Name: clients clients_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_pkey PRIMARY KEY (id);


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
-- Name: emergency_assignments emergency_assignments_emergency_report_id_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_assignments
    ADD CONSTRAINT emergency_assignments_emergency_report_id_key UNIQUE (emergency_report_id);


--
-- Name: emergency_assignments emergency_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_assignments
    ADD CONSTRAINT emergency_assignments_pkey PRIMARY KEY (id);


--
-- Name: emergency_reports emergency_reports_local_id_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_reports
    ADD CONSTRAINT emergency_reports_local_id_key UNIQUE (local_id);


--
-- Name: emergency_reports emergency_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_reports
    ADD CONSTRAINT emergency_reports_pkey PRIMARY KEY (id);


--
-- Name: emergency_status_history emergency_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_status_history
    ADD CONSTRAINT emergency_status_history_pkey PRIMARY KEY (id);


--
-- Name: emergency_tracking_points emergency_tracking_points_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_tracking_points
    ADD CONSTRAINT emergency_tracking_points_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: quotation_offers quotation_offers_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_offers
    ADD CONSTRAINT quotation_offers_pkey PRIMARY KEY (id);


--
-- Name: quotation_request_history quotation_request_history_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_request_history
    ADD CONSTRAINT quotation_request_history_pkey PRIMARY KEY (id);


--
-- Name: quotation_request_workshops quotation_request_workshops_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_request_workshops
    ADD CONSTRAINT quotation_request_workshops_pkey PRIMARY KEY (id);


--
-- Name: quotation_requests quotation_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_requests
    ADD CONSTRAINT quotation_requests_pkey PRIMARY KEY (id);


--
-- Name: sucursales sucursales_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.sucursales
    ADD CONSTRAINT sucursales_pkey PRIMARY KEY (id);


--
-- Name: technicians technicians_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.technicians
    ADD CONSTRAINT technicians_pkey PRIMARY KEY (id);


--
-- Name: usuarios_tenant usuarios_tenant_email_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.usuarios_tenant
    ADD CONSTRAINT usuarios_tenant_email_key UNIQUE (email);


--
-- Name: usuarios_tenant usuarios_tenant_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.usuarios_tenant
    ADD CONSTRAINT usuarios_tenant_pkey PRIMARY KEY (id);


--
-- Name: vehicles vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_pkey PRIMARY KEY (id);


--
-- Name: vehicles vehicles_plate_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_plate_key UNIQUE (plate);


--
-- Name: workshop_registrations workshop_registrations_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.workshop_registrations
    ADD CONSTRAINT workshop_registrations_pkey PRIMARY KEY (id);


--
-- Name: idx_quotation_offers_quotation_request_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_offers_quotation_request_id ON public.quotation_offers USING btree (quotation_request_id);


--
-- Name: idx_quotation_offers_workshop_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_offers_workshop_id ON public.quotation_offers USING btree (workshop_id);


--
-- Name: idx_quotation_request_history_request_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_request_history_request_id ON public.quotation_request_history USING btree (quotation_request_id);


--
-- Name: idx_quotation_request_workshops_quotation_request_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_request_workshops_quotation_request_id ON public.quotation_request_workshops USING btree (quotation_request_id);


--
-- Name: idx_quotation_request_workshops_workshop_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_request_workshops_workshop_id ON public.quotation_request_workshops USING btree (workshop_id);


--
-- Name: idx_quotation_requests_client_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_requests_client_id ON public.quotation_requests USING btree (client_id);


--
-- Name: idx_quotation_requests_emergency_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_requests_emergency_id ON public.quotation_requests USING btree (emergency_id);


--
-- Name: uq_quotation_offers_request_workshop; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE UNIQUE INDEX uq_quotation_offers_request_workshop ON public.quotation_offers USING btree (quotation_request_id, workshop_id);


--
-- Name: uq_quotation_request_workshops_request_workshop; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE UNIQUE INDEX uq_quotation_request_workshops_request_workshop ON public.quotation_request_workshops USING btree (quotation_request_id, workshop_id);


--
-- Name: emergency_assignments emergency_assignments_emergency_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_assignments
    ADD CONSTRAINT emergency_assignments_emergency_report_id_fkey FOREIGN KEY (emergency_report_id) REFERENCES public.emergency_reports(id) ON DELETE CASCADE;


--
-- Name: emergency_assignments emergency_assignments_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_assignments
    ADD CONSTRAINT emergency_assignments_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.technicians(id) ON DELETE RESTRICT;


--
-- Name: emergency_assignments emergency_assignments_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_assignments
    ADD CONSTRAINT emergency_assignments_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshop_registrations(id) ON DELETE CASCADE;


--
-- Name: emergency_reports emergency_reports_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_reports
    ADD CONSTRAINT emergency_reports_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE SET NULL;


--
-- Name: emergency_reports emergency_reports_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_reports
    ADD CONSTRAINT emergency_reports_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id) ON DELETE SET NULL;


--
-- Name: emergency_status_history emergency_status_history_emergency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_status_history
    ADD CONSTRAINT emergency_status_history_emergency_id_fkey FOREIGN KEY (emergency_id) REFERENCES public.emergency_reports(id) ON DELETE CASCADE;


--
-- Name: emergency_tracking_points emergency_tracking_points_emergency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_tracking_points
    ADD CONSTRAINT emergency_tracking_points_emergency_id_fkey FOREIGN KEY (emergency_id) REFERENCES public.emergency_reports(id) ON DELETE CASCADE;


--
-- Name: emergency_tracking_points emergency_tracking_points_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.emergency_tracking_points
    ADD CONSTRAINT emergency_tracking_points_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.technicians(id) ON DELETE SET NULL;


--
-- Name: quotation_offers quotation_offers_quotation_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_offers
    ADD CONSTRAINT quotation_offers_quotation_request_id_fkey FOREIGN KEY (quotation_request_id) REFERENCES public.quotation_requests(id) ON DELETE CASCADE;


--
-- Name: quotation_offers quotation_offers_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_offers
    ADD CONSTRAINT quotation_offers_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshop_registrations(id) ON DELETE CASCADE;


--
-- Name: quotation_request_history quotation_request_history_quotation_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_request_history
    ADD CONSTRAINT quotation_request_history_quotation_request_id_fkey FOREIGN KEY (quotation_request_id) REFERENCES public.quotation_requests(id) ON DELETE CASCADE;


--
-- Name: quotation_request_workshops quotation_request_workshops_quotation_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_request_workshops
    ADD CONSTRAINT quotation_request_workshops_quotation_request_id_fkey FOREIGN KEY (quotation_request_id) REFERENCES public.quotation_requests(id) ON DELETE CASCADE;


--
-- Name: quotation_request_workshops quotation_request_workshops_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_request_workshops
    ADD CONSTRAINT quotation_request_workshops_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshop_registrations(id) ON DELETE CASCADE;


--
-- Name: quotation_requests quotation_requests_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_requests
    ADD CONSTRAINT quotation_requests_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE SET NULL;


--
-- Name: quotation_requests quotation_requests_emergency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.quotation_requests
    ADD CONSTRAINT quotation_requests_emergency_id_fkey FOREIGN KEY (emergency_id) REFERENCES public.emergency_reports(id) ON DELETE CASCADE;


--
-- Name: technicians technicians_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.technicians
    ADD CONSTRAINT technicians_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id) ON DELETE SET NULL;


--
-- Name: technicians technicians_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.technicians
    ADD CONSTRAINT technicians_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshop_registrations(id) ON DELETE CASCADE;


--
-- Name: usuarios_tenant usuarios_tenant_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.usuarios_tenant
    ADD CONSTRAINT usuarios_tenant_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id) ON DELETE SET NULL;


--
-- Name: vehicles vehicles_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE;


--
-- Name: workshop_registrations workshop_registrations_sucursal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.workshop_registrations
    ADD CONSTRAINT workshop_registrations_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict bhYAuGpA1gyTZznmVtdGdF0deL9poUaTVMuqO239C30wEOl9WtWGv75kPmKYksx

