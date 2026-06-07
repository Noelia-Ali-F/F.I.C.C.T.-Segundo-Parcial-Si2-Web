--
-- PostgreSQL database dump
--

\restrict 63EfeKzxKJLc6K9GinhLiyyujXSUsqMihAK2d9qFOQbaoyoNL9zcWfavAPmng94

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
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    usuario_tenant_id bigint
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
-- Name: workshop_specialties; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.workshop_specialties (
    id bigint NOT NULL,
    workshop_id bigint NOT NULL,
    specialty character varying(120) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.workshop_specialties OWNER TO diagramador;

--
-- Name: workshop_specialties_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.workshop_specialties_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workshop_specialties_id_seq OWNER TO diagramador;

--
-- Name: workshop_specialties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.workshop_specialties_id_seq OWNED BY public.workshop_specialties.id;


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
-- Name: workshop_specialties id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.workshop_specialties ALTER COLUMN id SET DEFAULT nextval('public.workshop_specialties_id_seq'::regclass);


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.clients (id, identity_card, full_name, email, phone, password_hash, role, status, accepted_terms, created_at, updated_at) FROM stdin;
1	AN-CL-1001	Cliente A Auxilio Norte	cliente.a@auxilionorte.com	70010031	df3fe0cf1b4d763bf10d5c6d27204007$5069dda530fe4213d5fdf7c315c55e78cb865a06b631ed1c320937fe797441ad	CLIENTE	active	t	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
2	AN-CL-1002	Cliente B Auxilio Norte	cliente.b@auxilionorte.com	70010032	1387ca2c48f9c8d3ad5ae213454d21e5$9a635341236b7aae85d8d966622a065d91273870d6d6fb6d723cd09fb3fc04d9	CLIENTE	active	t	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
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
1	4	1	1	asignado	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
2	5	2	2	asignado	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
3	6	1	1	asignado	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
\.


--
-- Data for Name: emergency_reports; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_reports (id, local_id, client_id, vehicle_name, vehicle_plate, problem_type, price, emergency_status, problem_type_standardized, photo_problem_type_standardized, photo_classification_confidence, photo_classification_error, description, latitude, longitude, address, zone, nearest_workshop_id, nearest_workshop_name, nearest_workshop_specialty, nearest_workshop_zone, nearest_workshop_distance_meters, audio_duration_seconds, audio_transcript, audio_transcript_status, audio_transcript_error, photo_paths, photo_urls, audio_path, audio_url, rejection_reason, rejected_at, hora_llegada, latitud_llegada, longitud_llegada, sucursal_id, created_at, updated_at) FROM stdin;
1	AN-E-001	1	Toyota Hilux	AN-1001	Motor	120	pendiente	Motor	\N	\N	\N	Vehiculo no enciende	-17.751	-63.177	Av. Banzer km 9	Norte	\N	\N	\N	\N	\N	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	1	2026-06-04 23:38:31.861262+00	2026-06-04 23:38:31.861262+00
2	AN-E-002	2	Suzuki Swift	AN-1002	Bateria	60	activo	Bateria	\N	\N	\N	Bateria descargada	-17.829	-63.188	Canal Cotoca 4to anillo	Sur	2	Auxilio Norte Taller Sur	Bateria	Sur	2300	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	2	2026-06-05 21:38:31.861262+00	2026-06-05 21:53:31.861262+00
3	AN-E-003	1	Toyota Hilux	AN-1001	Motor	140	auxilio_asignado	Motor	\N	\N	\N	Falla electrica en ruta	-17.762	-63.171	Radial 26	Norte	1	Auxilio Norte Taller Norte	Motor	Norte	1500	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	\N	\N	\N	1	2026-06-06 01:38:31.861262+00	2026-06-06 02:08:31.861262+00
5	AN-E-005	2	Suzuki Swift	AN-1002	Bateria	80	servicio_en_proceso	Bateria	\N	\N	\N	Cambio de bateria en sitio	-17.831	-63.189	Av. Santos Dumont 6to anillo	Sur	2	Auxilio Norte Taller Sur	Bateria	Sur	900	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	2026-06-06 22:08:31.861262+00	\N	\N	2	2026-06-06 20:38:31.861262+00	2026-06-06 22:18:31.861262+00
6	AN-E-006	1	Toyota Hilux	AN-1001	Motor	190	servicio_finalizado	Motor	\N	\N	\N	Servicio finalizado con exito	-17.77	-63.175	Av. Cristo Redentor	Norte	1	Auxilio Norte Taller Norte	Motor	Norte	700	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	2026-06-04 06:08:31.861262+00	\N	\N	1	2026-06-04 05:38:31.861262+00	2026-06-04 06:38:31.861262+00
7	AN-E-007	2	Suzuki Swift	AN-1002	Bateria	0	solicitud_cancelada	Bateria	\N	\N	\N	Cliente cancelo la solicitud	-17.826	-63.185	Doble Via la Guardia	Sur	2	Auxilio Norte Taller Sur	Bateria	Sur	2100	\N	\N	\N	\N	[]	[]	\N	\N	Cliente resolvio por cuenta propia	2026-06-06 04:18:31.861262+00	\N	\N	\N	2	2026-06-06 03:38:31.861262+00	2026-06-06 04:18:31.861262+00
4	AN-E-004	1	Toyota Hilux	AN-1001	Motor	150	servicio_en_proceso	Motor	\N	\N	\N	Asistencia en desplazamiento	-17.764	-63.173	4to anillo y San Martin	Norte	1	Auxilio Norte Taller Norte	Motor	Norte	1200	\N	\N	\N	\N	[]	[]	\N	\N	\N	\N	2026-06-07 06:24:36.570746+00	-17.764	-63.173	1	2026-06-06 23:38:31.861262+00	2026-06-07 06:25:48.166332+00
\.


--
-- Data for Name: emergency_status_history; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_status_history (id, emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation, created_at) FROM stdin;
1	1	\N	pendiente	CLIENTE	1	Pendiente inicial	2026-06-04 23:38:31.861262+00
2	2	\N	pendiente	CLIENTE	2	Solicitud creada	2026-06-05 21:38:31.861262+00
3	2	pendiente	activo	ADMIN_SUCURSAL	3	Buscando taller	2026-06-05 21:53:31.861262+00
4	3	\N	pendiente	CLIENTE	1	Solicitud creada	2026-06-06 01:38:31.861262+00
5	3	pendiente	activo	ADMIN_SUCURSAL	2	Buscando taller	2026-06-06 01:53:31.861262+00
6	3	activo	auxilio_asignado	ADMIN_SUCURSAL	2	Taller asignado	2026-06-06 02:08:31.861262+00
7	4	\N	pendiente	CLIENTE	1	Solicitud creada	2026-06-06 23:38:31.861262+00
8	4	pendiente	activo	ADMIN_SUCURSAL	2	Buscando taller	2026-06-06 23:58:31.861262+00
9	4	activo	auxilio_asignado	ADMIN_SUCURSAL	2	Tecnico asignado	2026-06-07 00:13:31.861262+00
10	4	auxilio_asignado	auxilio_en_camino	TECNICO	4	En camino	2026-06-07 00:28:31.861262+00
11	5	\N	pendiente	CLIENTE	2	Solicitud creada	2026-06-06 20:38:31.861262+00
12	5	pendiente	activo	ADMIN_SUCURSAL	3	Buscando taller	2026-06-06 21:08:31.861262+00
13	5	activo	auxilio_asignado	ADMIN_SUCURSAL	3	Taller asignado	2026-06-06 21:33:31.861262+00
14	5	auxilio_asignado	auxilio_en_camino	TECNICO	5	En camino	2026-06-06 21:48:31.861262+00
15	5	auxilio_en_camino	tecnico_en_sitio	TECNICO	5	Tecnico en sitio	2026-06-06 22:08:31.861262+00
16	5	tecnico_en_sitio	servicio_en_proceso	TECNICO	5	En atencion	2026-06-06 22:18:31.861262+00
17	6	\N	pendiente	CLIENTE	1	Solicitud creada	2026-06-04 05:38:31.861262+00
18	6	pendiente	activo	ADMIN_SUCURSAL	2	Buscando taller	2026-06-04 05:48:31.861262+00
19	6	activo	auxilio_asignado	ADMIN_SUCURSAL	2	Taller asignado	2026-06-04 05:58:31.861262+00
20	6	auxilio_asignado	auxilio_en_camino	TECNICO	4	En camino	2026-06-04 06:03:31.861262+00
21	6	auxilio_en_camino	tecnico_en_sitio	TECNICO	4	Llegada	2026-06-04 06:08:31.861262+00
22	6	tecnico_en_sitio	servicio_en_proceso	TECNICO	4	Atendiendo	2026-06-04 06:13:31.861262+00
23	6	servicio_en_proceso	servicio_finalizado	ADMIN_SUCURSAL	2	Caso finalizado	2026-06-04 06:38:31.861262+00
24	7	\N	pendiente	CLIENTE	2	Solicitud creada	2026-06-06 03:38:31.861262+00
25	7	pendiente	activo	ADMIN_SUCURSAL	3	Buscando taller	2026-06-06 03:58:31.861262+00
26	7	activo	solicitud_cancelada	CLIENTE	2	Cancelada	2026-06-06 04:18:31.861262+00
27	4	auxilio_en_camino	tecnico_en_sitio	admin	\N	QA fase 15 tecnico en sitio	2026-06-07 06:24:36.570746+00
28	4	tecnico_en_sitio	servicio_en_proceso	TECNICO	4	QA fase 15 validacion actor tecnico	2026-06-07 06:25:48.166332+00
\.


--
-- Data for Name: emergency_tracking_points; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_tracking_points (id, emergency_id, technician_id, latitude, longitude, source, created_at) FROM stdin;
1	4	1	-17.761	-63.172	technician_app	2026-06-07 00:38:31.861262+00
2	4	1	-17.762	-63.1725	technician_app	2026-06-07 00:58:31.861262+00
3	4	1	-17.7641	-63.1731	technician_app	2026-06-07 06:24:36.609518+00
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.notifications (id, user_id, title, message, is_read, payload_json, created_at) FROM stdin;
1	1	Tecnico asignado	Tu caso ya tiene tecnico asignado.	f	\N	2026-06-07 05:38:30.847894+00
2	1	Estado actualizado	La emergencia AN-E-004 esta en camino.	f	\N	2026-06-07 05:38:30.847894+00
3	2	Caso cancelado	La emergencia AN-E-007 fue cancelada.	t	\N	2026-06-07 05:38:30.847894+00
4	1	Estado actualizado	Tu solicitud ahora está: Técnico en sitio	f	{"type": "emergency_status_updated", "emergency_id": "4", "status": "tecnico_en_sitio", "status_label": "Técnico en sitio"}	2026-06-07 06:24:36.580635+00
5	1	Estado actualizado	Tu solicitud ahora está: Servicio en proceso	f	{"type": "emergency_status_updated", "emergency_id": "4", "status": "servicio_en_proceso", "status_label": "Servicio en proceso"}	2026-06-07 06:25:48.175751+00
\.


--
-- Data for Name: quotation_offers; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_offers (id, quotation_request_id, workshop_id, workshop_rating, price, service_description, spare_parts, labor_detail, labor_cost, spare_parts_cost, estimated_service_time, offer_status, submitted_at, selected_at, created_at, updated_at, estimated_arrival_time, warranty, validity_days, observations, condiciones_servicio, status, expires_at) FROM stdin;
1	1	1	\N	180.00	Diagnostico y reparacion de arranque	\N	\N	\N	\N	90 min	pendiente	\N	\N	2026-06-07 02:53:31.861262+00	2026-06-07 05:38:30.847894+00	20 min	30 dias	2	Incluye prueba en ruta	\N	aceptada	2026-06-09 02:53:31.861262+00
2	1	2	\N	210.00	Diagnostico y reparacion de arranque	\N	\N	\N	\N	120 min	pendiente	\N	\N	2026-06-07 02:58:31.861262+00	2026-06-07 05:38:30.847894+00	30 min	15 dias	2	Sin repuestos premium	\N	rechazada	2026-06-09 02:58:31.861262+00
\.


--
-- Data for Name: quotation_request_history; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_request_history (id, quotation_request_id, event_type, detail, actor_role, actor_user_id, created_at) FROM stdin;
1	1	solicitud_creada	Solicitud de cotizacion creada	system	1	2026-06-07 02:38:31.861262+00
2	1	cotizacion_enviada	Oferta enviada por taller norte	workshop	1	2026-06-07 02:53:31.861262+00
3	1	cotizacion_enviada	Oferta enviada por taller sur	workshop	2	2026-06-07 02:58:31.861262+00
4	1	cotizacion_aceptada	Cliente acepta oferta ganadora	CLIENTE	1	2026-06-07 03:13:31.861262+00
5	1	taller_descartado	Oferta de taller sur rechazada	CLIENTE	1	2026-06-07 03:13:31.861262+00
\.


--
-- Data for Name: quotation_request_workshops; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_request_workshops (id, quotation_request_id, workshop_id, status, notified_at, created_at) FROM stdin;
1	1	1	respondido	2026-06-07 02:38:31.861262+00	2026-06-07 02:38:31.861262+00
2	1	2	respondido	2026-06-07 02:38:31.861262+00	2026-06-07 02:38:31.861262+00
\.


--
-- Data for Name: quotation_requests; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_requests (id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at) FROM stdin;
1	4	1	seleccionado	2	2	1	2026-06-07 02:38:31.861262+00	2026-06-08 02:38:31.861262+00	2026-06-07 02:38:31.861262+00	2026-06-07 02:38:31.861262+00
\.


--
-- Data for Name: sucursales; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.sucursales (id, nombre, direccion, zona, ciudad, latitud, longitud, telefono, responsable, estado, created_at, updated_at) FROM stdin;
1	Sucursal Norte	Av. Banzer 1234	Norte	Santa Cruz	-17.7534	-63.1768	70010011	Rosa Perez	activo	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
2	Sucursal Sur	Av. Santos Dumont 5421	Sur	Santa Cruz	-17.8348	-63.1902	70010012	Luis Arce	activo	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
\.


--
-- Data for Name: technicians; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.technicians (id, workshop_id, full_name, phone, email, specialty, status, sucursal_id, created_at, updated_at, usuario_tenant_id) FROM stdin;
1	1	Tecnico Norte	70010051	tecnico.op.norte@auxilionorte.com	Motor	ocupado	1	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00	4
2	2	Tecnico Sur	70010052	tecnico.op.sur@auxilionorte.com	Bateria	disponible	2	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00	5
\.


--
-- Data for Name: usuarios_tenant; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.usuarios_tenant (id, email, full_name, phone, password_hash, role, sucursal_id, estado, created_at, updated_at) FROM stdin;
1	superadmin@auxilionorte.com	Superadmin Auxilio Norte	70010021	616997832bd453a7804f4bdcbe4d2952$707db7a72b69d520a49f2bc2767e80e30b46cff170833118021f975c8d7c6232	SUPERADMIN_TENANT	\N	activo	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
2	admin.norte@auxilionorte.com	Admin Sucursal Norte	70010022	99b8a7b0ed3e46e07ad8d9d1a172e228$9a0baed23072e6da3ae91a60d4647426e954c1421e3dd113c61917f7d6102271	ADMIN_SUCURSAL	1	activo	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
3	admin.sur@auxilionorte.com	Admin Sucursal Sur	70010023	631fe2f20725f9fe9e869d6a12f67963$6a9862671b0506a949f974b5dc379a577a0627d34efc94a054d1cb4bb59cd157	ADMIN_SUCURSAL	2	activo	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
4	tecnico.norte@auxilionorte.com	Tecnico Norte	70010024	da4d693fd8b7e88b2c89a2bf1ce12bfb$c0922edf6b9b72533ae52d66f8a282ed7b5ebfe3bada57a035b7eab55f496bf6	TECNICO	1	activo	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
5	tecnico.sur@auxilionorte.com	Tecnico Sur	70010025	de68ccd7a6e10bebb6181725961bbb00$9cf2d66d6c70ec58ff099cfd0c449251ccbcba55176327302bff01ad3930d18b	TECNICO	2	activo	2026-06-07 05:38:30.847894+00	2026-06-07 05:38:30.847894+00
\.


--
-- Data for Name: vehicles; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.vehicles (id, client_id, brand, model, year, plate, color, is_primary, photo_path, photo_url, created_at) FROM stdin;
1	1	Toyota	Hilux	2021	AN-1001	Blanco	t	\N	\N	2026-06-07 05:38:30.847894+00
2	2	Suzuki	Swift	2020	AN-1002	Rojo	t	\N	\N	2026-06-07 05:38:30.847894+00
\.


--
-- Data for Name: workshop_registrations; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.workshop_registrations (id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, availability_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, sucursal_id, created_at) FROM stdin;
1	Auxilio Norte Taller Norte	Rosa Perez	70010041	taller.norte@auxilionorte.com	Norte	Batería	activo	disponible	1f58ab56c095620136bd59679ab0a883$750e691f26ee9e67d380c27e48594e3713e6cb46791fa7dbf146911e7ae48e11	-17.7534	-63.1768	America/La_Paz	-240	1	2026-06-07 05:38:30.847894+00
2	Auxilio Norte Taller Sur	Luis Arce	70010042	taller.sur@auxilionorte.com	Sur	Motor	activo	disponible	18e8b195c2f89eaf37a8be137525cf76$eae1d3ba8bec5b04cd8ccc9b7e75ee9ac86a9bf51238273a88607ab042359f97	-17.8348	-63.1902	America/La_Paz	-240	2	2026-06-07 05:38:30.847894+00
3	Auxilio Norte Sucursal Temporal QA	QA Demo	70099999	sucursal.4@auxilio-norte.local	Centro	Motor	rechazado	fuera_de_servicio	\N	-17.78	-63.18	\N	\N	\N	2026-06-07 12:05:46.035748+00
4	Auxilio Norte Sucursal Temporal QA 2	QA Demo 2	70088888	sucursal.5@auxilio-norte.local	Centro	Motor	rechazado	fuera_de_servicio	\N	-17.781	-63.181	\N	\N	\N	2026-06-07 12:06:14.957767+00
\.


--
-- Data for Name: workshop_specialties; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.workshop_specialties (id, workshop_id, specialty, created_at) FROM stdin;
1	1	Batería	2026-06-07 12:04:06.599688+00
2	1	Electricidad	2026-06-07 12:04:06.599688+00
3	1	Llanta	2026-06-07 12:04:06.599688+00
4	2	Motor	2026-06-07 12:04:06.599688+00
5	2	Choque	2026-06-07 12:04:06.599688+00
6	2	Mecánica general	2026-06-07 12:04:06.599688+00
9	3	Motor	2026-06-07 12:05:46.057974+00
10	3	Llanta	2026-06-07 12:05:46.057974+00
11	3	Grúa	2026-06-07 12:05:46.057974+00
14	4	Motor	2026-06-07 12:06:14.979423+00
15	4	Llanta	2026-06-07 12:06:14.979423+00
16	4	Grúa	2026-06-07 12:06:14.979423+00
\.


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.clients_id_seq', 2, true);


--
-- Name: device_fcm_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.device_fcm_tokens_id_seq', 1, false);


--
-- Name: emergency_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_assignments_id_seq', 3, true);


--
-- Name: emergency_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_reports_id_seq', 7, true);


--
-- Name: emergency_status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_status_history_id_seq', 28, true);


--
-- Name: emergency_tracking_points_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_tracking_points_id_seq', 3, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.notifications_id_seq', 5, true);


--
-- Name: quotation_offers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_offers_id_seq', 2, true);


--
-- Name: quotation_request_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_request_history_id_seq', 5, true);


--
-- Name: quotation_request_workshops_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_request_workshops_id_seq', 2, true);


--
-- Name: quotation_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_requests_id_seq', 1, true);


--
-- Name: sucursales_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.sucursales_id_seq', 5, true);


--
-- Name: technicians_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.technicians_id_seq', 2, true);


--
-- Name: usuarios_tenant_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.usuarios_tenant_id_seq', 5, true);


--
-- Name: vehicles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.vehicles_id_seq', 2, true);


--
-- Name: workshop_registrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.workshop_registrations_id_seq', 4, true);


--
-- Name: workshop_specialties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.workshop_specialties_id_seq', 16, true);


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
-- Name: workshop_specialties workshop_specialties_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.workshop_specialties
    ADD CONSTRAINT workshop_specialties_pkey PRIMARY KEY (id);


--
-- Name: workshop_specialties workshop_specialties_workshop_id_specialty_key; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.workshop_specialties
    ADD CONSTRAINT workshop_specialties_workshop_id_specialty_key UNIQUE (workshop_id, specialty);


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
-- Name: workshop_specialties_specialty_idx; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX workshop_specialties_specialty_idx ON public.workshop_specialties USING btree (specialty);


--
-- Name: workshop_specialties_workshop_id_idx; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX workshop_specialties_workshop_id_idx ON public.workshop_specialties USING btree (workshop_id);


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
-- Name: technicians technicians_usuario_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.technicians
    ADD CONSTRAINT technicians_usuario_tenant_id_fkey FOREIGN KEY (usuario_tenant_id) REFERENCES public.usuarios_tenant(id) ON DELETE SET NULL;


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
-- Name: workshop_specialties workshop_specialties_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.workshop_specialties
    ADD CONSTRAINT workshop_specialties_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshop_registrations(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 63EfeKzxKJLc6K9GinhLiyyujXSUsqMihAK2d9qFOQbaoyoNL9zcWfavAPmng94

