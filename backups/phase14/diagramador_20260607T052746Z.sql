--
-- PostgreSQL database dump
--

\restrict 9APdWqnRpCuhOBZnJdn04DUnTd46OgQfHf2Eeu0LJkTD6njcB2Rd4d9kIEVYQtK

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
    role character varying(40) DEFAULT 'client'::character varying NOT NULL,
    status character varying(30) DEFAULT 'active'::character varying NOT NULL,
    accepted_terms boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    rejection_reason text,
    rejected_at timestamp with time zone,
    local_id character varying(64),
    hora_llegada timestamp with time zone,
    latitud_llegada double precision,
    longitud_llegada double precision,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1,
    sucursal_id bigint
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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    estimated_service_time character varying(80),
    estimated_arrival_time character varying(80),
    warranty character varying(255),
    validity_days integer,
    observations text,
    status character varying(30) DEFAULT 'enviada'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    spare_parts text,
    labor_detail text,
    labor_cost numeric(12,2),
    spare_parts_cost numeric(12,2),
    condiciones_servicio text,
    tenant_id bigint DEFAULT 1
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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1,
    sucursal_id bigint
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
-- Name: tenants; Type: TABLE; Schema: public; Owner: diagramador
--

CREATE TABLE public.tenants (
    id bigint NOT NULL,
    nombre character varying(200) NOT NULL,
    descripcion text,
    estado character varying(30) DEFAULT 'activo'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tenants OWNER TO diagramador;

--
-- Name: tenants_id_seq; Type: SEQUENCE; Schema: public; Owner: diagramador
--

CREATE SEQUENCE public.tenants_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tenants_id_seq OWNER TO diagramador;

--
-- Name: tenants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: diagramador
--

ALTER SEQUENCE public.tenants_id_seq OWNED BY public.tenants.id;


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
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id bigint DEFAULT 1
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
    password_hash character varying(255),
    latitude double precision,
    longitude double precision,
    timezone character varying(120),
    utc_offset_minutes integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    availability_status character varying(30) DEFAULT 'disponible'::character varying NOT NULL,
    tenant_id bigint DEFAULT 1,
    sucursal_id bigint
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
-- Name: technicians id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.technicians ALTER COLUMN id SET DEFAULT nextval('public.technicians_id_seq'::regclass);


--
-- Name: tenants id; Type: DEFAULT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.tenants ALTER COLUMN id SET DEFAULT nextval('public.tenants_id_seq'::regclass);


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

COPY public.clients (id, identity_card, full_name, email, phone, password_hash, role, status, accepted_terms, created_at, updated_at, tenant_id) FROM stdin;
1	9882105	Noelia Fernandez	noelia@gmail.com	75560845	50f06992f7ac866a5924ad9f57a99e39$7da1cad5d6429aaaa7316970991cac5a05f10dc6e45573c63f8205544b2fc81e	client	active	t	2026-05-28 00:32:03.496777+00	2026-05-28 00:32:03.496777+00	1
2	10001780783745	Smoke Usuario A 1780783745	smokea_1780783745@emergencias.bo	70003745	aab1ea099c68a9bd56cae1a411145c88$69ce72325b971966f6b195ba4163d26c0fb06bcc1b81f07256c578dd428183eb	client	active	t	2026-06-06 22:09:05.389712+00	2026-06-06 22:09:05.389712+00	1
3	20001780783772	Smoke Usuario B 1780783772	smokeb_1780783772@emergencias.bo	71113772	cf934e02b72bd1f9666ee08d5d6ae8dc$36decdec6ef431e0044f41c4c4729361c54bd36e3a588b3457caea4dc2a0cfa8	client	active	t	2026-06-06 22:09:31.728752+00	2026-06-06 22:09:31.728752+00	1
4	CI1780788624	Fase 65 Usuario B 1780788624	fase65b_1780788624@emergencias.bo	70012345	be6b499b98a4f88e2af093814a751e2b$fa3a6680a2381b97dcac24d31ec938f0ceba7952a8ed13d53f77eac19b6430f5	client	active	t	2026-06-06 23:30:24.234681+00	2026-06-06 23:30:24.234681+00	1
5	7867498	Fase 68 Usuario B	fase68b_1780791466@emergencias.bo	71155962	1917f5dd535365fa3e8ae3b7ef66cf01$0ec41ea00c21c4a997b289cc3969497f266635f0f46fba262255205721e6b96e	client	active	t	2026-06-07 00:17:46.823027+00	2026-06-07 00:17:46.823027+00	1
\.


--
-- Data for Name: device_fcm_tokens; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.device_fcm_tokens (id, user_id, fcm_token, platform, is_active, created_at, updated_at, tenant_id) FROM stdin;
120	1	fcm_demo_token_1234567890_ABCDEFGHIJKLMNOPQRSTUVWXYZ	android	f	2026-06-07 01:00:39.104632+00	2026-06-07 01:00:39.439056+00	1
122	2	legacy_u2_token_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890	android	t	2026-06-07 01:28:23.601021+00	2026-06-07 01:28:23.601021+00	1
34	1	eg1fni9LTeiHlx7jIxi0q9:APA91bHs3k0cZH3aJ-EwpLg9kjqUIZNvxlHKIlNrDbJDKGNBezLeLgPWgsGQNEduT4wOMy4qvUxDP826G4vrz8M11XHlvqvng1vw-EQ-hApjPKorqaT_Iuk	android	t	2026-05-29 16:10:37.556717+00	2026-05-29 18:50:07.746106+00	1
39	1	cDdDpkTUR3mHmdWUhoT0Zb:APA91bGFdzHMOzQ_X20W_IkUs0vtpSdsGRb8J2yJ2tLtRziAPp6ySCRIj7E-GnaeszVYXcj74ulMoqMQSO-PIv990zii1yS26FxQiZ7fnntT6iGh8bPDflM	android	t	2026-05-29 18:55:55.978331+00	2026-05-29 19:07:31.977134+00	1
75	2	elY-2NhiT9CFDB-Wre6uTM:APA91bGxcwzaGKgS7kz6VGEMMMPMspTXzaqaUUW0B7GO0-jcMF0K591unG8QVlPXSROaF0juXnWp3ZQUC6vQVBxa1b4clpryZDS5zkXx2nDVOunqym1MJ8E	android	t	2026-06-06 23:02:26.364354+00	2026-06-06 23:29:33.048812+00	1
1	1	fE1XUQkHSLKSmxt-ecjDHP:APA91bEVsHOxfni0g_cVCTgaj40ligTCctKpZX_ILP8_7XTR0YCFNzbUr2xTK82zo6STCTte98a0uunC16qpHKTeMJ8EpVWrwpcxf4k8rRCTHHscn0uo3TM	android	t	2026-05-28 00:32:05.883434+00	2026-05-28 03:31:44.23611+00	1
11	1	ckg4nUOES3OiSgEsFQ0y21:APA91bELMpDs0xeytULYJd0Kc7lroD8D3HcpqZ36gHcyrlqhZ8CzPSA_C0ZGmQIrKxad206fAffHocfJ9vjfkVUxPwiRVw626j8iqT_B0aO6jEH0EZPtgNg	android	t	2026-05-28 03:50:58.698981+00	2026-05-28 03:54:47.083377+00	1
14	1	eVsituaBQfaQwGgAF9Hqp0:APA91bFVBgWakzl2ZmEAMrC-M_aPtI-yLjmi4CdyWGpjGMTnPfKqP1cBxwat8vUSedJFFrEr5V_HoNvbFkbPLcjIP10-zEZt79pqMsT6mOQcJkCBeZbqnUs	android	t	2026-05-28 04:09:05.186693+00	2026-05-28 04:09:05.186693+00	1
15	1	cAZOWG8FRdqHf4kYPW_oCL:APA91bH5hu3Fb4OOUXLpjwaSDXgNV60-AdmJMzYyPQ4PQ1PGZTVpmP9VfPChfzmNS063aMLNlIuG8rHt_cBd2WPd2tJdzRafJRfwKEEq0AUf1on3GQLFpik	android	t	2026-05-28 15:58:49.96069+00	2026-05-28 15:58:49.96069+00	1
41	1	ewfXNFOsS7-JMmxo5si976:APA91bFJE6JYEXJAkS4vy1TfHKIWfSb50KLH_wv1AKCQFRz6TeQceQRSxqZ_0tkMy2j9AA-yJdMrt5kkYJ2HyHH2Md92ef9QsduloYo2AzMvbdpZ6bHFv-8	android	t	2026-05-30 19:43:09.146339+00	2026-05-30 19:52:34.146746+00	1
55	1	eZr0ou1uSg2J_J34NcmKeo:APA91bHVK1L9m7OCDM7fcXgtYFhTjwVvq4Wj3rJS4vJkujXT-ySaY77o-rlBW2Rc7xnPyE9TE4kwWw4j9O4AVymWoC3W81DniqMDnB7A24iCKJMK8vyE0iE	android	t	2026-06-05 23:21:12.775842+00	2026-06-06 02:22:32.412727+00	1
16	1	ekGx3PytRmWGCcOd3DP9bC:APA91bHMVupxlTLLS24kiz4nAMo_dNDMEJ-aWJibqYw2FBe0-lREFzhlHSerXzB6AjC9xr53knUUrCQt4uyp-yZER69uqKM4NuD_9jtQb5BApc05bGcjrR0	android	t	2026-05-28 17:15:21.801782+00	2026-05-29 08:13:05.112626+00	1
66	1	eEwWEnpDSSuGZ8NaZSoj8B:APA91bEbrznYbvbC-ob6VlPmbtdDB5NSh8q0IM0nuqdNuPHT85D3GqyKjC-58w8ynsk2EO0A3bc2IEnsjWv-SWBbYLxznz435BSd0YHP7KK834NFj5nZbx4	android	t	2026-06-06 04:44:58.891011+00	2026-06-06 18:26:05.37383+00	1
23	1	cWb_YIcmR_-Q7vXZO7MGMs:APA91bFJXosLMh3YLR59HsC97M6rswsHFzS8woaZvkZQtmvPHhFRC-TqvqXHSdE3M067sAxlEQ_1mritRKxoJUG6OnfcP4P9cxa-aXhs5oXy_xlKiCtLHRs	android	t	2026-05-29 08:17:55.089355+00	2026-05-29 14:44:14.815777+00	1
30	1	dEWYCvO_QkuQ8VKac0m1qP:APA91bHCmwIh4Yf-t66qSHyH8A52fLwk2ofybBCF4eZnMkFekixK2xcO9EcJ-90w5kNhWGBsUnPI8uYjAB7ZkXahC0vGzd__0eIFg3yE6bXR_NgcBxYuVC4	android	t	2026-05-29 15:23:28.910682+00	2026-05-29 15:28:50.32894+00	1
32	1	dMl4KNAMTnWNrOkLBc_oMo:APA91bGqBu0HglQ3RwSZ9uR4mndUi8USpuXTuaPlo68DDmjkk9f6QOP1g0IvBa5P4HhN4Y88WI_7QOtb3OPOrwO-x6lBzeYCcyDc8DsxDIi-aS_IimmyKVo	android	t	2026-05-29 15:45:44.960875+00	2026-05-29 15:45:44.960875+00	1
33	1	fDfhk_kATiSPBLfg5Sy-CU:APA91bGnVDw7AdVdOIIiYk_bx0WvgASiWhL31JfiYfFTCNO5AZI3PCjGD929R3HjsMCP7lregFG9OMJpmjU0EU4LK7HYTi9nzD5x-aHbNkBA9HlVa0CUbjc	android	t	2026-05-29 15:58:24.664055+00	2026-05-29 15:58:24.664055+00	1
45	1	fxpdhWETSz6zyPf65Y1KJz:APA91bGcicR8-vSreY-wQDmV-EBwGOUWBjozrfm0pnCaGgT-2fDwk647GE5UXy3SOdcmteoe-kYg3EG5d-8JfpsXjzpPSZKmN1XFQ2Nv2gV86gqEwGmcl_k	android	t	2026-05-30 20:00:37.086767+00	2026-06-05 18:45:04.095627+00	1
71	1	fo6VuXkNRL6qzk7dIqFQpo:APA91bE43Oe0XLKhF8_5IHNtK7hiRSTdZ_7HcsCbwK_kWedQc9Xmw9NAuK5J_5y3gnMkLU0JkULvS_bLmBgJCjiTD7yFaX5N95TCqYjh00k1aJLbNyDD4wU	android	t	2026-06-06 22:32:30.876656+00	2026-06-06 22:35:47.026833+00	1
73	1	ekdI0_m3Tl6UXobShYkqYB:APA91bHyCM-ctTuVllVR6DCIoLxJplpHDvdmwxtmsP8i0OhLmW35yhDVOQXAR13Fy-kCScbEZaoCtYgcVLJPsbojXfN_PzcxUlHT-4LAtf5cqpruEUtynj8	android	t	2026-06-06 22:40:43.221063+00	2026-06-06 22:44:41.113379+00	1
82	2	eAMzGfSTQ5-AZ6S2BKwaIm:APA91bG2_LFfkt8rXv7mqJEm_7x7_33oNnKWJrLqONuatNpvrombmZn8upn3AbD8R288B-xvAAax2wLR_rNRzJfI72DKZOkAMKC66eQIDDN4nsEvKmkaJwA	android	t	2026-06-06 23:50:21.23425+00	2026-06-07 00:38:12.623048+00	1
\.


--
-- Data for Name: emergency_assignments; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_assignments (id, emergency_report_id, workshop_id, technician_id, assignment_status, created_at, updated_at, tenant_id) FROM stdin;
1	3	1	1	asignado	2026-05-28 03:28:54.740641+00	2026-05-28 03:28:54.740641+00	1
7	12	1	1	asignado	2026-05-29 04:28:25.891056+00	2026-05-29 04:28:25.891056+00	1
8	24	1	2	asignado	2026-05-29 16:13:42.614972+00	2026-05-29 16:13:42.614972+00	1
10	39	1	1	asignado	2026-06-06 03:57:36.236841+00	2026-06-06 03:57:36.236841+00	1
9	37	1	3	asignado	2026-06-05 23:55:52.013814+00	2026-06-06 05:39:25.167256+00	1
\.


--
-- Data for Name: emergency_reports; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_reports (id, client_id, vehicle_name, vehicle_plate, problem_type, price, emergency_status, problem_type_standardized, photo_problem_type_standardized, photo_classification_confidence, photo_classification_error, description, latitude, longitude, address, zone, nearest_workshop_id, nearest_workshop_name, nearest_workshop_specialty, nearest_workshop_zone, nearest_workshop_distance_meters, audio_duration_seconds, audio_transcript, audio_transcript_status, audio_transcript_error, photo_paths, photo_urls, audio_path, audio_url, created_at, rejection_reason, rejected_at, local_id, hora_llegada, latitud_llegada, longitud_llegada, updated_at, tenant_id, sucursal_id) FROM stdin;
3	1	Hilux RTXL 2024	2906SEX	Batería	50	activo	Batería	\N	\N	\N	\N	-17.7819459	-63.1947038	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.69	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-28 03:26:51.012782+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
4	1	Toyots Corolls 2026	5678TYV	Batería	50	en_revision	Batería	\N	\N	\N	\N	-17.7819586	-63.1947101	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	2	PowerAuto	Batería	zona centro	2119.0597185685333	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-28 03:32:03.200009+00	no hay tecnicos	2026-05-29 14:29:07.85735+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
18	1	Hilux RTXL 2024	2906SEX	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7819499	-63.1947051	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.8	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 14:32:44.393361+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
2	1	Hilux RTXL 2024	2906SEX	Batería	50	activo	Batería	\N	\N	\N	\N	-17.7819518	-63.1947053	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.78	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-28 03:03:44.384986+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
10	1	Toyots Corolls 2026	5678TYV	Batería	50	solicitud_cancelada	Batería	\N	\N	\N	\N	-17.7819476	-63.1947044	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.78	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 04:02:35.808698+00	No hay técnicos disponibles en este momento	2026-05-29 08:01:23.986744+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
11	1	QA Vehiculo Integral	QAT601	Batería	50	servicio_finalizado	Batería	\N	\N	\N	Prueba integral QA desde terminal	-17.7819482	-63.1947024	Equipetrol, Santa Cruz	Equipetrol	1	ElectroCar	Batería	zona centro	1071	\N	\N	\N	\N	["emergencias/photos/d5e8153c342b4ce9b4ec0fe094fd8c92.jpeg"]	["/uploads/emergencias/photos/d5e8153c342b4ce9b4ec0fe094fd8c92.jpeg"]	\N	\N	2026-05-29 04:27:09.918579+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
9	\N	Vehiculo Timeline	TL6FF504	Batería	50	solicitud_cancelada	Batería	\N	\N	\N	\N	\N	\N	\N	\N	1	ElectroCar	Batería	zona centro	\N	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 04:00:17.244757+00	No hay técnicos disponibles en este momento	2026-05-29 08:02:47.349014+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
21	1	Hilux RTXL 2024	2906SEX	Batería	50	servicio_en_proceso	Batería	\N	\N	\N	\N	-17.7819503	-63.1947048	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	2	PowerAuto	Batería	zona centro	2118.069975294134	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 15:23:53.299653+00	no hay tecnicos	2026-05-29 15:24:43.059201+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
7	1	Hilux RTXL 2024	2906SEX	Batería	50	en_revision	Batería	\N	\N	\N	\N	-17.7819485	-63.1947023	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	2	PowerAuto	Batería	zona centro	2117.836222658413	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-28 04:09:29.027968+00	No hay tecnicos disponibles en este momento	2026-05-29 13:52:43.508246+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
16	1	Hilux RTXL 2024	2906SEX	Batería	50	solicitud_cancelada	Batería	\N	\N	\N	\N	-17.7819495	-63.1947062	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.68	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 08:18:16.493939+00	no hay tecnicos disponibles	2026-05-29 08:20:34.407345+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
15	1	Toyots Corolls 2026	5678TYV	Batería	50	solicitud_cancelada	Batería	\N	\N	\N	\N	-17.7819493	-63.1947041	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.88	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 08:13:21.604057+00	no hay tecnicos	2026-05-29 08:22:02.508936+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
13	1	Hilux RTXL 2024	2906SEX	Batería	50	servicio_finalizado	Batería	\N	\N	\N	\N	-17.78195	-63.1947099	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.33	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 04:29:07.194505+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
6	1	Hilux RTXL 2024	2906SEX	Batería	50	solicitud_cancelada	Batería	\N	\N	\N	\N	-17.7819426	-63.1947052	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.51	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-28 03:55:03.726754+00	No hay tecnicos disponibles en este momento	2026-05-29 13:53:04.089256+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
12	1	QA Compat Legacy	QAT602	Batería	50	servicio_en_proceso	Batería	\N	\N	\N	Prueba compatibilidad legacy	-17.7819482	-63.1947024	Equipetrol, Santa Cruz	Equipetrol	1	ElectroCar	Batería	zona centro	1071	\N	\N	\N	\N	["emergencias/photos/32dabba46ec54f73a25db50b49a1a516.jpeg"]	["/uploads/emergencias/photos/32dabba46ec54f73a25db50b49a1a516.jpeg"]	\N	\N	2026-05-29 04:28:16.26031+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
8	1	Hilux RTXL 2024	2906SEX	Batería	50	solicitud_cancelada	Batería	\N	\N	\N	\N	-17.7819482	-63.1947024	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1071	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-28 17:15:44.12894+00	No hay tecnicos disponibles en este momento	2026-05-29 13:52:01.087299+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
17	1	Hilux RTXL 2024	2906SEX	Batería	50	solicitud_cancelada	Batería	\N	\N	\N	\N	-17.781963	-63.1947089	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.92	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 14:23:24.479899+00	no hay tecnicos	2026-05-29 14:23:59.451446+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
23	1	Hilux RTXL 2024	2906SEX	Batería	50	auxilio_en_camino	Batería	\N	\N	\N	\N	-17.7819487	-63.1947027	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.99	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 15:58:45.886901+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
5	1	Hilux RTXL 2024	2906SEX	Batería	50	en_revision	Batería	\N	\N	\N	\N	-17.7819537	-63.1947083	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	2	PowerAuto	Batería	zona centro	2118.4942428634236	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-28 03:51:20.560715+00	no hay tecnicos	2026-05-29 14:27:57.666015+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
19	1	Hilux RTXL 2024	2906SEX	Batería	50	en_revision	Batería	\N	\N	\N	\N	-17.7819509	-63.1947039	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	2	PowerAuto	Batería	zona centro	2118.1233458898387	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 14:34:36.322235+00	no hay tecnicos	2026-05-29 14:36:00.266867+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
20	1	Hilux RTXL 2024	2906SEX	Batería	50	auxilio_asignado	Batería	\N	\N	\N	\N	-17.7819609	-63.1947105	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	2	PowerAuto	Batería	zona centro	2119.3188356288674	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 14:37:32.484495+00	no hay tecnicosssssssssssssssssss	2026-05-29 14:38:07.543883+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
14	1	Hilux RTXL 2024	2906SEX	Batería	50	servicio_en_proceso	Batería	\N	\N	\N	\N	-17.7819479	-63.1947022	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	2	PowerAuto	Batería	zona centro	2117.7686890841687	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 08:11:38.150916+00	No hay tecnicos disponibles en este momento	2026-05-29 13:51:20.911932+00	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
22	1	Hilux RTXL 2024	2906SEX	Batería	50	auxilio_en_camino	Batería	\N	\N	\N	\N	-17.7819484	-63.1947027	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.98	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 15:46:11.722888+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
24	1	Toyots Corolls 2026	5678TYV	Batería	50	servicio_finalizado	Batería	\N	\N	\N	\N	-17.7819373	-63.1947084	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 16:10:59.16551+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
25	1	Hilux RTXL 2024	2906SEX	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7819406	-63.1947029	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.67	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 18:47:02.972847+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
26	1	Hilux RTXL 2024	2906SEX	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7819645	-63.1947082	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	\N	\N	\N	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 18:57:15.710708+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
27	\N	TestAuto QA	QA-001	Batería	50	pendiente	Batería	\N	\N	\N	Test QA sin local_id	-17.7863	-63.1812	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 20:18:53.588594+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
28	\N	TestAuto QA Offline	QA-002	Neumático	50	pendiente	Neumático	\N	\N	\N	Test QA con local_id nuevo	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 20:19:56.01574+00	\N	\N	qa-test-1780085995-5661	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
29	\N	QA Final Test	QA-F01	Motor	100	solicitud_cancelada	Motor	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-29 20:27:52.044747+00	Test QA rechazo	2026-05-29 20:30:24.323107+00	qa-final-1780086472	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
30	1	Toyots Corolls 2026	5678TYV	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7819491	-63.1947041	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.87	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-02 15:52:28.604728+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
31	1	Hilux RTXL 2024	2906SEX	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7819471	-63.1947014	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1071.06	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-05 18:15:04.960783+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
32	1	Toyots Corolls 2026	5678TYV	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7817617	-63.1945683	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	\N	\N	\N	4.993	\N	disabled	\N	[]	[]	emergencias/audio/9817aefeac434ca1bb5a2787fe8ea4c7.m4a	/uploads/emergencias/audio/9817aefeac434ca1bb5a2787fe8ea4c7.m4a	2026-06-05 18:45:20.518261+00	\N	\N	local_1780683487004997	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
33	1	Toyots Corolls 2026	5678TYV	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7819429	-63.1947025	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	\N	\N	\N	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-05 23:21:51.036049+00	\N	\N	local_1780701700461902	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
34	1	Hilux RTXL 2024	2906SEX	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7819593	-63.1947101	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.66	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-05 23:22:59.874366+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
35	1	Toyots Corolls 2026	5678TYV	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7819482	-63.1947064	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.61	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-05 23:29:44.252656+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
37	1	Toyots Corolls 2026	5678TYV	Batería	50	activo	Batería	\N	\N	\N	\N	-17.7819479	-63.1947021	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1071.02	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-05 23:49:31.921606+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:50:41.760173+00	1	\N
38	1	Toyots Corolls 2026	5678TYV	Batería	50	activo	Batería	\N	\N	\N	\N	-17.7819415	-63.1947036	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.63	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-05 23:59:44.546175+00	\N	\N	\N	\N	\N	\N	2026-06-06 03:57:23.780108+00	1	\N
39	1	Hilux RTXL 2024	2906SEX	Batería	50	servicio_en_proceso	Batería	\N	\N	\N	\N	-17.7819631	-63.1947085	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1070.96	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-06 01:22:03.290132+00	\N	\N	\N	2026-06-06 04:05:05.81934+00	-17.7833	-63.1821	2026-06-06 04:07:56.530753+00	1	\N
36	1	Toyots Corolls 2026	5678TYV	Batería	50	auxilio_asignado	Batería	\N	\N	\N	\N	-17.7819512	-63.1947015	6R94+846, Distrito Municipal 1, Santa Cruz de la Sierra\nEquipetrol	Equipetrol	1	ElectroCar	Batería	zona centro	1071.21	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-05 23:46:54.861953+00	\N	\N	\N	\N	\N	\N	2026-06-06 05:19:28.477773+00	1	\N
40	2	SmokeCar A	SMK2A	Batería	50	pendiente	Batería	\N	\N	\N	\N	-17.7833	-63.1821	Smoke manual push	Centro	\N	\N	\N	\N	\N	\N	\N	\N	\N	[]	[]	\N	\N	2026-06-06 22:21:36.48638+00	\N	\N	\N	\N	\N	\N	2026-06-06 22:21:36.48638+00	1	\N
1	1	Toyots Corolls 2026	5678TYV	Batería	50	auxilio_en_camino	Batería	\N	\N	\N	\N	-17.7833	-63.1821	6R89+M4H, Centro, Santa Cruz de la Sierra\nCentro	Centro	1	ElectroCar	Batería	zona centro	1070.85	\N	\N	\N	\N	[]	[]	\N	\N	2026-05-28 02:31:17.973914+00	\N	\N	\N	\N	\N	\N	2026-06-07 04:11:26.017564+00	1	\N
\.


--
-- Data for Name: emergency_status_history; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_status_history (id, emergency_id, previous_status, new_status, changed_by_role, changed_by_user_id, observation, created_at, tenant_id) FROM stdin;
1	9	\N	solicitud_recibida	\N	\N	\N	2026-05-29 04:00:17.244757+00	1
2	9	pendiente	auxilio_en_camino	workshop	1	El técnico salió del taller	2026-05-29 04:00:17.271772+00	1
3	9	auxilio_en_camino	activo	workshop	1	\N	2026-05-29 04:00:17.293154+00	1
4	10	\N	solicitud_recibida	client	1	\N	2026-05-29 04:02:35.808698+00	1
5	8	activo	en_revision	workshop	1	Prueba FCM estado	2026-05-29 04:16:50.241397+00	1
6	8	en_revision	auxilio_en_camino	workshop	1	Prueba FCM estado 2	2026-05-29 04:17:23.822565+00	1
7	8	auxilio_en_camino	activo	workshop	1	\N	2026-05-29 04:17:38.947632+00	1
8	11	\N	solicitud_recibida	client	1	\N	2026-05-29 04:27:09.918579+00	1
9	11	pendiente	en_revision	workshop	1	QA step 1	2026-05-29 04:27:38.414277+00	1
10	11	en_revision	auxilio_asignado	workshop	1	QA step 2	2026-05-29 04:27:38.697126+00	1
11	11	auxilio_asignado	auxilio_en_camino	workshop	1	QA step 3	2026-05-29 04:27:38.950476+00	1
12	11	auxilio_en_camino	servicio_en_proceso	workshop	1	QA step 4	2026-05-29 04:27:39.225755+00	1
13	11	servicio_en_proceso	servicio_finalizado	workshop	1	QA step 5	2026-05-29 04:27:39.449405+00	1
14	12	\N	solicitud_recibida	client	1	\N	2026-05-29 04:28:16.26031+00	1
15	12	pendiente	activo	workshop	1	\N	2026-05-29 04:28:25.614436+00	1
16	13	\N	solicitud_recibida	client	1	\N	2026-05-29 04:29:07.194505+00	1
17	13	pendiente	en_revision	admin	\N	Cambio realizado desde dashboard web	2026-05-29 04:29:57.149419+00	1
18	13	en_revision	auxilio_asignado	admin	\N	Cambio realizado desde dashboard web	2026-05-29 04:31:17.892613+00	1
19	13	auxilio_asignado	auxilio_en_camino	admin	\N	Cambio realizado desde dashboard web	2026-05-29 04:43:49.514278+00	1
20	13	auxilio_en_camino	servicio_en_proceso	admin	\N	Cambio realizado desde dashboard web	2026-05-29 04:51:31.321599+00	1
21	13	servicio_en_proceso	servicio_finalizado	admin	\N	Cambio realizado desde dashboard web	2026-05-29 05:02:01.668824+00	1
22	12	activo	auxilio_en_camino	admin	\N	Cambio realizado desde dashboard web	2026-05-29 07:14:28.618609+00	1
23	12	auxilio_en_camino	servicio_en_proceso	admin	\N	Cambio realizado desde dashboard web	2026-05-29 07:14:34.92608+00	1
24	10	pendiente	solicitud_cancelada	workshop	1	No hay técnicos disponibles en este momento · Técnicos disponibles: 0	2026-05-29 08:01:23.987847+00	1
25	9	activo	solicitud_cancelada	workshop	1	No hay técnicos disponibles en este momento	2026-05-29 08:02:47.350016+00	1
26	14	\N	solicitud_recibida	client	1	\N	2026-05-29 08:11:38.150916+00	1
27	14	pendiente	en_revision	admin	\N	Cambio realizado desde dashboard web	2026-05-29 08:12:31.71876+00	1
28	15	\N	solicitud_recibida	client	1	\N	2026-05-29 08:13:21.604057+00	1
29	16	\N	solicitud_recibida	client	1	\N	2026-05-29 08:18:16.493939+00	1
30	16	pendiente	solicitud_cancelada	admin	\N	no hay tecnicos disponibles	2026-05-29 08:20:34.407931+00	1
31	15	pendiente	solicitud_cancelada	admin	0	no hay tecnicos	2026-05-29 08:22:02.509836+00	1
32	14	en_revision	solicitud_cancelada	workshop	1	No hay tecnicos disponibles en este momento	2026-05-29 13:51:20.913102+00	1
33	14	solicitud_cancelada	en_revision	workshop	1	Solicitud reasignada automaticamente al taller PowerAuto	2026-05-29 13:51:20.928207+00	1
34	8	activo	solicitud_cancelada	workshop	1	No hay tecnicos disponibles en este momento	2026-05-29 13:52:01.088092+00	1
35	8	solicitud_cancelada	solicitud_cancelada	workshop	1	No se encontro taller alternativo disponible	2026-05-29 13:52:01.102256+00	1
36	7	activo	solicitud_cancelada	workshop	1	No hay tecnicos disponibles en este momento	2026-05-29 13:52:43.509152+00	1
37	7	solicitud_cancelada	en_revision	workshop	1	Solicitud reasignada automaticamente al taller PowerAuto	2026-05-29 13:52:43.523695+00	1
38	6	activo	solicitud_cancelada	workshop	1	No hay tecnicos disponibles en este momento	2026-05-29 13:53:04.090381+00	1
39	6	solicitud_cancelada	solicitud_cancelada	workshop	1	No se encontro taller alternativo disponible	2026-05-29 13:53:04.108048+00	1
40	17	\N	solicitud_recibida	client	1	\N	2026-05-29 14:23:24.479899+00	1
41	17	pendiente	solicitud_cancelada	admin	0	no hay tecnicos	2026-05-29 14:23:59.452547+00	1
42	17	solicitud_cancelada	solicitud_cancelada	admin	0	No se encontro taller alternativo disponible	2026-05-29 14:23:59.462301+00	1
43	5	activo	solicitud_cancelada	admin	0	no hay tecnicos	2026-05-29 14:27:57.667058+00	1
44	5	solicitud_cancelada	en_revision	admin	0	Solicitud reasignada automaticamente al taller PowerAuto	2026-05-29 14:27:57.687114+00	1
45	4	activo	solicitud_cancelada	admin	0	no hay tecnicos	2026-05-29 14:29:07.858119+00	1
46	4	solicitud_cancelada	en_revision	admin	0	Solicitud reasignada automaticamente al taller PowerAuto	2026-05-29 14:29:07.873294+00	1
47	18	\N	solicitud_recibida	client	1	\N	2026-05-29 14:32:44.393361+00	1
48	19	\N	solicitud_recibida	client	1	\N	2026-05-29 14:34:36.322235+00	1
49	19	pendiente	solicitud_cancelada	admin	0	no hay tecnicos	2026-05-29 14:36:00.26764+00	1
50	19	solicitud_cancelada	en_revision	admin	0	Solicitud reasignada automaticamente al taller PowerAuto	2026-05-29 14:36:00.280111+00	1
51	20	\N	solicitud_recibida	client	1	\N	2026-05-29 14:37:32.484495+00	1
52	20	pendiente	solicitud_cancelada	admin	0	no hay tecnicosssssssssssssssssss	2026-05-29 14:38:07.544578+00	1
53	20	solicitud_cancelada	en_revision	admin	0	Solicitud reasignada automaticamente al taller PowerAuto	2026-05-29 14:38:07.558873+00	1
54	20	en_revision	auxilio_asignado	workshop	2	Cambio realizado desde dashboard web	2026-05-29 14:43:53.685945+00	1
55	21	\N	solicitud_recibida	client	1	\N	2026-05-29 15:23:53.299653+00	1
56	21	pendiente	solicitud_cancelada	admin	0	no hay tecnicos	2026-05-29 15:24:43.060104+00	1
57	21	solicitud_cancelada	en_revision	admin	0	Solicitud reasignada automaticamente al taller PowerAuto	2026-05-29 15:24:43.071848+00	1
58	21	en_revision	auxilio_asignado	workshop	2	Cambio realizado desde dashboard web	2026-05-29 15:25:15.262993+00	1
59	21	auxilio_asignado	auxilio_en_camino	workshop	2	Cambio realizado desde dashboard web	2026-05-29 15:25:47.158689+00	1
60	21	auxilio_en_camino	servicio_en_proceso	workshop	2	Cambio realizado desde dashboard web	2026-05-29 15:25:58.427355+00	1
61	14	en_revision	auxilio_asignado	workshop	2	Cambio realizado desde dashboard web	2026-05-29 15:28:05.944483+00	1
62	14	auxilio_asignado	auxilio_en_camino	workshop	2	Cambio realizado desde dashboard web	2026-05-29 15:28:18.951313+00	1
63	14	auxilio_en_camino	servicio_en_proceso	workshop	2	Cambio realizado desde dashboard web	2026-05-29 15:29:02.915617+00	1
64	22	\N	solicitud_recibida	client	1	\N	2026-05-29 15:46:11.722888+00	1
65	22	pendiente	en_revision	workshop	1	Cambio realizado desde dashboard web	2026-05-29 15:47:22.439774+00	1
69	23	pendiente	en_revision	workshop	1	Cambio realizado desde dashboard web	2026-05-29 15:59:22.556533+00	1
73	24	pendiente	en_revision	workshop	1	Cambio realizado desde dashboard web	2026-05-29 16:13:16.717807+00	1
75	24	activo	auxilio_en_camino	workshop	1	Cambio realizado desde dashboard web	2026-05-29 16:15:27.373364+00	1
66	22	en_revision	auxilio_asignado	workshop	1	Cambio realizado desde dashboard web	2026-05-29 15:47:32.248818+00	1
74	24	en_revision	activo	workshop	1	\N	2026-05-29 16:13:28.238002+00	1
76	24	auxilio_en_camino	servicio_en_proceso	workshop	1	Cambio realizado desde dashboard web	2026-05-29 16:16:24.0225+00	1
67	22	auxilio_asignado	auxilio_en_camino	workshop	1	Cambio realizado desde dashboard web	2026-05-29 15:47:52.863244+00	1
70	23	en_revision	auxilio_asignado	workshop	1	Cambio realizado desde dashboard web	2026-05-29 15:59:26.286212+00	1
77	24	servicio_en_proceso	servicio_finalizado	workshop	1	Cambio realizado desde dashboard web	2026-05-29 16:16:28.031057+00	1
68	23	\N	solicitud_recibida	client	1	\N	2026-05-29 15:58:45.886901+00	1
72	24	\N	solicitud_recibida	client	1	\N	2026-05-29 16:10:59.16551+00	1
71	23	auxilio_asignado	auxilio_en_camino	workshop	1	Cambio realizado desde dashboard web	2026-05-29 15:59:35.078558+00	1
78	25	\N	solicitud_recibida	client	1	\N	2026-05-29 18:47:02.972847+00	1
79	26	\N	solicitud_recibida	client	1	\N	2026-05-29 18:57:15.710708+00	1
80	27	\N	solicitud_recibida	\N	\N	\N	2026-05-29 20:18:53.588594+00	1
81	28	\N	solicitud_recibida	\N	\N	\N	2026-05-29 20:19:56.01574+00	1
82	29	\N	solicitud_recibida	\N	\N	\N	2026-05-29 20:27:52.044747+00	1
83	29	pendiente	solicitud_cancelada	admin	\N	Test QA rechazo	2026-05-29 20:30:24.32414+00	1
84	29	solicitud_cancelada	solicitud_cancelada	admin	\N	No se encontro taller alternativo disponible	2026-05-29 20:30:24.333994+00	1
85	30	\N	solicitud_recibida	client	1	\N	2026-06-02 15:52:28.604728+00	1
86	31	\N	solicitud_recibida	client	1	\N	2026-06-05 18:15:04.960783+00	1
87	32	\N	solicitud_recibida	client	1	\N	2026-06-05 18:45:20.518261+00	1
88	33	\N	solicitud_recibida	client	1	\N	2026-06-05 23:21:51.036049+00	1
89	34	\N	solicitud_recibida	client	1	\N	2026-06-05 23:22:59.874366+00	1
90	35	\N	solicitud_recibida	client	1	\N	2026-06-05 23:29:44.252656+00	1
91	36	\N	solicitud_recibida	client	1	\N	2026-06-05 23:46:54.861953+00	1
92	37	\N	solicitud_recibida	client	1	\N	2026-06-05 23:49:31.921606+00	1
93	37	pendiente	en_revision	workshop	1	Cambio realizado desde dashboard web	2026-06-05 23:55:13.855709+00	1
94	37	en_revision	activo	workshop	1	\N	2026-06-05 23:55:41.622774+00	1
95	38	\N	solicitud_recibida	client	1	\N	2026-06-05 23:59:44.546175+00	1
96	39	\N	solicitud_recibida	client	1	\N	2026-06-06 01:22:03.290132+00	1
97	39	pendiente	en_revision	workshop	1	Cambio realizado desde dashboard web	2026-06-06 03:51:51.978546+00	1
98	39	en_revision	activo	workshop	1	\N	2026-06-06 03:52:03.492367+00	1
99	38	pendiente	en_revision	workshop	1	Cambio realizado desde dashboard web	2026-06-06 03:57:18.907995+00	1
100	38	en_revision	activo	workshop	1	\N	2026-06-06 03:57:23.780108+00	1
101	39	activo	auxilio_en_camino	workshop	1	Cambio realizado desde dashboard web	2026-06-06 03:57:51.924193+00	1
102	39	auxilio_en_camino	tecnico_en_sitio	admin	\N	\N	2026-06-06 03:59:35.521596+00	1
103	39	tecnico_en_sitio	auxilio_en_camino	admin	\N	\N	2026-06-06 04:05:04.843433+00	1
104	39	auxilio_en_camino	tecnico_en_sitio	admin	\N	\N	2026-06-06 04:05:05.81934+00	1
105	39	tecnico_en_sitio	servicio_en_proceso	admin	\N	\N	2026-06-06 04:07:56.530753+00	1
106	36	pendiente	auxilio_asignado	workshop	1	\N	2026-06-06 05:19:28.477773+00	1
107	40	\N	solicitud_recibida	client	2	\N	2026-06-06 22:21:36.48638+00	1
108	1	activo	auxilio_en_camino	admin	\N	\N	2026-06-07 04:11:24.890436+00	1
109	1	auxilio_en_camino	auxilio_en_camino	admin	\N	\N	2026-06-07 04:11:26.017564+00	1
\.


--
-- Data for Name: emergency_tracking_points; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.emergency_tracking_points (id, emergency_id, technician_id, latitude, longitude, source, created_at, tenant_id) FROM stdin;
1	3	1	-17.775	-63.19	system	2026-05-29 15:08:45.62475+00	1
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.notifications (id, user_id, title, message, is_read, payload_json, created_at, tenant_id) FROM stdin;
1	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "11", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:04:49.86293+00	1
2	1	Nueva propuesta recibida	ElectroCar envió una cotización: Bs. 450.00	f	{"type": "quotation_offer_received", "quotation_id": "11", "emergency_id": "38", "status": "con_propuestas", "workshop_name": "ElectroCar", "price": "450.0"}	2026-06-06 01:05:06.935669+00	1
3	1	Nueva propuesta recibida	ElectroCar envió una cotización: Bs. 520.00	f	{"type": "quotation_offer_received", "quotation_id": "11", "emergency_id": "38", "status": "con_propuestas", "workshop_name": "ElectroCar", "price": "520.0"}	2026-06-06 01:05:24.961126+00	1
4	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "12", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:06:51.255928+00	1
5	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "12", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:06:51.876861+00	1
6	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "12", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:06:51.88184+00	1
7	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "12", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:06:51.886926+00	1
8	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "12", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:06:51.891852+00	1
9	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "13", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:08:51.991217+00	1
10	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "13", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:08:52.684264+00	1
11	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "13", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:08:52.688675+00	1
12	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "13", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:08:52.693181+00	1
13	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "13", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:08:52.697254+00	1
14	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "14", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:13:45.238672+00	1
15	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "14", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:13:45.929102+00	1
16	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "14", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:13:45.933762+00	1
17	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "14", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:13:45.938178+00	1
18	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "14", "emergency_id": "38", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:13:45.943377+00	1
19	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "15", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:23:28.248438+00	1
20	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "15", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:23:28.916905+00	1
21	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "15", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:23:28.922543+00	1
22	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "15", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:23:28.927247+00	1
23	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "15", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:23:28.932246+00	1
24	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "16", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:33:04.899812+00	1
25	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "16", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:33:05.61324+00	1
26	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "16", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:33:05.618217+00	1
27	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "16", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:33:05.622632+00	1
28	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "16", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:33:05.627101+00	1
29	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "17", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:24.211143+00	1
30	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "17", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:24.914592+00	1
31	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "17", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:24.921707+00	1
32	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "17", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:24.929158+00	1
33	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "17", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:24.935677+00	1
34	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "18", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:32.162532+00	1
35	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "18", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:32.839839+00	1
36	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "18", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:32.845103+00	1
37	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "18", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:32.849431+00	1
38	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "18", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:43:32.853653+00	1
39	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "19", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:50:45.012833+00	1
40	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "19", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:50:45.710418+00	1
41	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "19", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:50:45.716578+00	1
42	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "19", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:50:45.72154+00	1
43	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "19", "emergency_id": "37", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 01:50:45.729034+00	1
44	1	Nueva propuesta recibida	ElectroCar envió una cotización: Bs. 420.00	f	{"type": "quotation_offer_received", "quotation_id": "19", "emergency_id": "37", "status": "con_propuestas", "workshop_name": "ElectroCar", "price": "420.0"}	2026-06-06 01:51:06.93335+00	1
45	1	Nueva propuesta recibida	PowerAuto envió una cotización: Bs. 460.00	f	{"type": "quotation_offer_received", "quotation_id": "19", "emergency_id": "37", "status": "con_propuestas", "workshop_name": "PowerAuto", "price": "460.0"}	2026-06-06 01:51:07.001609+00	1
46	1	¡Propuesta seleccionada!	Tu cotización de Bs. 420.00 fue seleccionada por el cliente.	f	{"type": "quotation_offer_selected", "quotation_id": "19", "emergency_id": "37", "status": "seleccionado", "workshop_name": "", "price": "420.0"}	2026-06-06 01:51:29.741044+00	1
47	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "20", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:07:59.504451+00	1
48	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "20", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:08:00.456788+00	1
49	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "20", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:08:00.462731+00	1
50	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "20", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:08:00.467829+00	1
51	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "20", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:08:00.47382+00	1
52	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "21", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:23:59.011231+00	1
53	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "21", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:23:59.724549+00	1
54	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "21", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:23:59.731404+00	1
55	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "21", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:23:59.736552+00	1
56	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "21", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 02:23:59.740873+00	1
57	1	Nueva cotización recibida	Un taller ha enviado una propuesta para tu emergencia. Precio: Bs. 190.00	f	{"quotation_id": 21, "offer_id": 11, "workshop_name": "ElectroCar", "price": "190.00"}	2026-06-06 02:28:12.751892+00	1
58	1	Nueva propuesta recibida	ElectroCar envió una cotización: Bs. 190.00	f	{"type": "quotation_offer_received", "quotation_id": "21", "emergency_id": "39", "status": "con_propuestas", "workshop_name": "ElectroCar", "price": "190.0"}	2026-06-06 02:28:12.758378+00	1
59	1	Nueva cotización recibida	Un taller ha enviado una propuesta para tu emergencia. Precio: Bs. 120.00	f	{"quotation_id": 21, "offer_id": 12, "workshop_name": "PowerAuto", "price": "120.00"}	2026-06-06 02:29:16.11061+00	1
60	1	Nueva propuesta recibida	PowerAuto envió una cotización: Bs. 120.00	f	{"type": "quotation_offer_received", "quotation_id": "21", "emergency_id": "39", "status": "con_propuestas", "workshop_name": "PowerAuto", "price": "120.0"}	2026-06-06 02:29:16.116243+00	1
61	1	¡Propuesta seleccionada!	Tu cotización de Bs. 190.00 fue seleccionada por el cliente.	f	{"type": "quotation_offer_selected", "quotation_id": "21", "emergency_id": "39", "status": "seleccionado", "workshop_name": "", "price": "190.0"}	2026-06-06 02:30:25.337839+00	1
62	1	Nueva cotización recibida	Un taller ha enviado una propuesta para tu emergencia. Precio: Bs. 350.00	f	{"quotation_id": 20, "offer_id": 13, "workshop_name": "ElectroCar", "price": "350.00"}	2026-06-06 02:45:27.721792+00	1
63	1	Nueva propuesta recibida	ElectroCar envió una cotización: Bs. 350.00	f	{"type": "quotation_offer_received", "quotation_id": "20", "emergency_id": "39", "status": "con_propuestas", "workshop_name": "ElectroCar", "price": "350.0"}	2026-06-06 02:45:27.725435+00	1
64	1	Cotización actualizada	Un taller actualizó su propuesta para tu emergencia. Precio: Bs. 390.00	f	{"quotation_id": 20, "offer_id": 13, "workshop_name": "ElectroCar", "price": "390.00"}	2026-06-06 02:45:36.507134+00	1
65	1	Nueva propuesta recibida	ElectroCar envió una cotización: Bs. 390.00	f	{"type": "quotation_offer_received", "quotation_id": "20", "emergency_id": "39", "status": "con_propuestas", "workshop_name": "ElectroCar", "price": "390.0"}	2026-06-06 02:45:36.51024+00	1
66	1	¡Propuesta seleccionada!	Tu cotización de Bs. 390.00 fue seleccionada por el cliente.	f	{"type": "quotation_offer_selected", "quotation_id": "20", "emergency_id": "39", "status": "seleccionado", "workshop_name": "", "price": "390.0"}	2026-06-06 02:45:51.045924+00	1
67	1	Estado actualizado	Tu solicitud ahora está: En revisión	f	{"type": "emergency_status_updated", "emergency_id": "39", "status": "en_revision", "status_label": "En revisión"}	2026-06-06 03:51:51.989136+00	1
68	1	Emergencia aceptada	ElectroCar acepto tu emergencia: Batería	f	{"type": "emergency_accepted", "emergency_id": "39", "workshop_id": "1", "workshop_name": "ElectroCar", "incident_description": "Batería"}	2026-06-06 03:52:03.502051+00	1
69	1	Estado actualizado	Tu solicitud ahora está: En revisión	f	{"type": "emergency_status_updated", "emergency_id": "38", "status": "en_revision", "status_label": "En revisión"}	2026-06-06 03:57:18.917964+00	1
70	1	Emergencia aceptada	ElectroCar acepto tu emergencia: Batería	f	{"type": "emergency_accepted", "emergency_id": "38", "workshop_id": "1", "workshop_name": "ElectroCar", "incident_description": "Batería"}	2026-06-06 03:57:23.789656+00	1
71	1	Tecnico asignado	carlos ramirez de ElectroCar atendera: Batería	f	{"type": "technician_assigned", "emergency_id": "39", "workshop_id": "1", "technician_id": "1", "workshop_name": "ElectroCar", "technician_name": "carlos ramirez", "incident_description": "Batería", "technician_latitude": "-17.778684693540267", "technician_longitude": "-63.20420698292684"}	2026-06-06 03:57:36.251497+00	1
72	1	Estado actualizado	Tu solicitud ahora está: Auxilio en camino	f	{"type": "emergency_status_updated", "emergency_id": "39", "status": "auxilio_en_camino", "status_label": "Auxilio en camino"}	2026-06-06 03:57:51.930653+00	1
73	1	Estado actualizado	Tu solicitud ahora está: Técnico en sitio	f	{"type": "emergency_status_updated", "emergency_id": "39", "status": "tecnico_en_sitio", "status_label": "Técnico en sitio"}	2026-06-06 03:59:35.530676+00	1
74	1	Estado actualizado	Tu solicitud ahora está: Auxilio en camino	f	{"type": "emergency_status_updated", "emergency_id": "39", "status": "auxilio_en_camino", "status_label": "Auxilio en camino"}	2026-06-06 04:05:04.852457+00	1
75	1	Estado actualizado	Tu solicitud ahora está: Técnico en sitio	f	{"type": "emergency_status_updated", "emergency_id": "39", "status": "tecnico_en_sitio", "status_label": "Técnico en sitio"}	2026-06-06 04:05:05.826734+00	1
76	1	Estado actualizado	Tu solicitud ahora está: Servicio en proceso	f	{"type": "emergency_status_updated", "emergency_id": "39", "status": "servicio_en_proceso", "status_label": "Servicio en proceso"}	2026-06-06 04:07:56.539291+00	1
77	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "22", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:45:20.01241+00	1
78	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "22", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:45:20.832658+00	1
79	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "22", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:45:20.837922+00	1
80	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "22", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:45:20.843376+00	1
81	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "22", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:45:20.848483+00	1
82	1	Nueva cotización recibida	Un taller ha enviado una propuesta para tu emergencia. Precio: Bs. 200.00	f	{"quotation_id": 22, "offer_id": 14, "workshop_name": "ElectroCar", "price": "200.00"}	2026-06-06 04:46:15.549766+00	1
83	1	Nueva propuesta recibida	ElectroCar envió una cotización: Bs. 200.00	f	{"type": "quotation_offer_received", "quotation_id": "22", "emergency_id": "36", "status": "con_propuestas", "workshop_name": "ElectroCar", "price": "200.0"}	2026-06-06 04:46:15.553517+00	1
84	1	Nueva cotización recibida	Un taller ha enviado una propuesta para tu emergencia. Precio: Bs. 500.00	f	{"quotation_id": 22, "offer_id": 15, "workshop_name": "PowerAuto", "price": "500.00"}	2026-06-06 04:46:53.720815+00	1
85	1	Nueva propuesta recibida	PowerAuto envió una cotización: Bs. 500.00	f	{"type": "quotation_offer_received", "quotation_id": "22", "emergency_id": "36", "status": "con_propuestas", "workshop_name": "PowerAuto", "price": "500.0"}	2026-06-06 04:46:53.723837+00	1
86	1	¡Propuesta seleccionada!	Tu cotización de Bs. 200.00 fue seleccionada por el cliente.	f	{"type": "quotation_offer_selected", "quotation_id": "22", "emergency_id": "36", "status": "seleccionado", "workshop_name": "", "price": "200.0"}	2026-06-06 04:49:37.369231+00	1
87	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "23", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:50:58.537082+00	1
88	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "23", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:50:59.195638+00	1
93	1	Nueva propuesta recibida	ElectroCar envió una cotización: Bs. 800.00	f	{"type": "quotation_offer_received", "quotation_id": "23", "emergency_id": "36", "status": "con_propuestas", "workshop_name": "ElectroCar", "price": "800.0"}	2026-06-06 04:51:20.4658+00	1
89	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "23", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:50:59.200693+00	1
90	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "23", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:50:59.205273+00	1
92	1	Nueva cotización recibida	Un taller ha enviado una propuesta para tu emergencia. Precio: Bs. 800.00	f	{"quotation_id": 23, "offer_id": 16, "workshop_name": "ElectroCar", "price": "800.00"}	2026-06-06 04:51:20.46042+00	1
95	1	Nueva propuesta recibida	PowerAuto envió una cotización: Bs. 700.00	f	{"type": "quotation_offer_received", "quotation_id": "23", "emergency_id": "36", "status": "con_propuestas", "workshop_name": "PowerAuto", "price": "700.0"}	2026-06-06 04:51:42.673663+00	1
96	2	¡Propuesta seleccionada!	Tu cotización de Bs. 700.00 fue seleccionada por el cliente.	f	{"type": "quotation_offer_selected", "quotation_id": "23", "emergency_id": "36", "status": "seleccionado", "workshop_name": "", "price": "700.0"}	2026-06-06 04:52:03.802869+00	1
91	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "23", "emergency_id": "36", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 04:50:59.21126+00	1
94	1	Nueva cotización recibida	Un taller ha enviado una propuesta para tu emergencia. Precio: Bs. 700.00	f	{"quotation_id": 23, "offer_id": 17, "workshop_name": "PowerAuto", "price": "700.00"}	2026-06-06 04:51:42.670871+00	1
97	1	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "24", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 05:01:36.301479+00	1
98	2	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "24", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 05:01:37.337247+00	1
99	6	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "24", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 05:01:37.344118+00	1
100	3	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "24", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 05:01:37.349825+00	1
101	4	Nueva solicitud de cotización	Se te ha invitado a cotizar una emergencia vehicular.	f	{"type": "quotation_request_sent", "quotation_id": "24", "emergency_id": "39", "status": "abierto", "workshop_name": "", "price": ""}	2026-06-06 05:01:37.354556+00	1
102	1	¡Propuesta seleccionada!	Tu cotización de Bs. 520.00 fue seleccionada por el cliente.	f	{"type": "quotation_offer_selected", "quotation_id": "11", "emergency_id": "38", "status": "seleccionado", "workshop_name": "", "price": "520.0"}	2026-06-06 05:08:15.044455+00	1
103	1	Estado actualizado	Tu solicitud ahora está: Auxilio asignado	f	{"type": "emergency_status_updated", "emergency_id": "36", "status": "auxilio_asignado", "status_label": "Auxilio asignado"}	2026-06-06 05:19:28.48792+00	1
104	1	Tecnico asignado	carlos ramirez de ElectroCar atendera: Batería	f	{"type": "technician_assigned", "emergency_id": "37", "workshop_id": "1", "technician_id": "1", "workshop_name": "ElectroCar", "technician_name": "carlos ramirez", "incident_description": "Batería", "technician_latitude": "-17.778684693540267", "technician_longitude": "-63.20420698292684"}	2026-06-06 05:21:48.202491+00	1
105	1	Tecnico asignado	carlos ramirez de ElectroCar atendera: Batería	f	{"type": "technician_assigned", "emergency_id": "37", "workshop_id": "1", "technician_id": "1", "workshop_name": "ElectroCar", "technician_name": "carlos ramirez", "incident_description": "Batería", "technician_latitude": "-17.778684693540267", "technician_longitude": "-63.20420698292684"}	2026-06-06 05:27:37.110423+00	1
106	1	Tecnico asignado	leon de ElectroCar atendera: Batería	f	{"type": "technician_assigned", "emergency_id": "37", "workshop_id": "1", "technician_id": "3", "workshop_name": "ElectroCar", "technician_name": "leon", "incident_description": "Batería", "technician_latitude": "-17.778684693540267", "technician_longitude": "-63.20420698292684"}	2026-06-06 05:39:25.176864+00	1
107	1	Estado actualizado	Tu solicitud ahora está: Auxilio en camino	f	{"type": "emergency_status_updated", "emergency_id": "1", "status": "auxilio_en_camino", "status_label": "Auxilio en camino"}	2026-06-07 04:11:24.904035+00	1
108	1	Estado actualizado	Tu solicitud ahora está: Auxilio en camino	f	{"type": "emergency_status_updated", "emergency_id": "1", "status": "auxilio_en_camino", "status_label": "Auxilio en camino"}	2026-06-07 04:11:26.024644+00	1
\.


--
-- Data for Name: quotation_offers; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_offers (id, quotation_request_id, workshop_id, workshop_rating, price, service_description, estimated_service_time, estimated_arrival_time, warranty, validity_days, observations, status, created_at, expires_at, spare_parts, labor_detail, labor_cost, spare_parts_cost, condiciones_servicio, tenant_id) FROM stdin;
1	1	6	\N	150.00	Servicio de emergencia completo con repuestos originales	2 horas	20 minutos	6 meses	3	\N	enviada	2026-06-05 21:35:30.880825+00	2026-06-08 21:35:30.879423+00	\N	\N	\N	\N	\N	1
2	2	6	\N	350.50	Diagnóstico completo de batería y reemplazo si es necesario	2 horas	30 minutos	6 meses en repuestos	3	Incluye revisión eléctrica sin costo adicional	enviada	2026-06-05 23:07:24.030845+00	2026-06-08 23:07:24.030022+00	\N	\N	\N	\N	\N	1
3	3	5	\N	280.00	Servicio de prueba uno	\N	\N	\N	3	\N	enviada	2026-06-05 23:08:07.892678+00	2026-06-08 23:08:07.891441+00	\N	\N	\N	\N	\N	1
4	3	4	\N	310.00	Servicio de prueba dos	\N	\N	\N	3	\N	enviada	2026-06-05 23:08:08.50321+00	2026-06-08 23:08:08.502586+00	\N	\N	\N	\N	\N	1
5	6	1	\N	530.00	Cambio de batería, revisión eléctrica y prueba final	\N	\N	\N	3	\N	enviada	2026-06-06 00:42:16.524887+00	2026-06-09 00:42:16.523372+00	\N	\N	\N	\N	\N	1
6	7	2	\N	620.00	Reposición de batería y verificación del sistema de carga	2 horas	20 minutos	6 meses	7	Incluye revisión de bornes y limpieza	enviada	2026-06-06 00:43:04.445741+00	2026-06-13 00:43:04.445345+00	Batería 12V 75Ah AGM	Desinstalación, instalación, prueba de alternador y escaneo básico	90.00	530.00	\N	1
7	10	1	\N	410.00	Cambio de batería y revisión del sistema de carga	90 minutos	20 minutos	3 meses	2	Incluye prueba final	aceptada	2026-06-06 00:55:47.9876+00	2026-06-08 00:55:47.982132+00	Batería 12V 75Ah	Instalación, prueba eléctrica y limpieza de bornes	70.00	340.00	\N	1
9	19	1	\N	420.00	Cambio de batería, prueba de carga y revisión eléctrica	90 minutos	20 minutos	3 meses	2	Incluye revisión final	aceptada	2026-06-06 01:51:06.923984+00	2026-06-08 01:51:06.914954+00	Batería 12V 75Ah	Instalación y prueba eléctrica	70.00	350.00	\N	1
10	19	2	\N	460.00	Cambio de batería premium y limpieza de bornes	1 hora	25 minutos	6 meses	2	Incluye prueba de alternador	rechazada	2026-06-06 01:51:06.99353+00	2026-06-08 01:51:06.984257+00	Batería premium 12V	Instalación, limpieza y prueba	80.00	380.00	\N	1
11	21	1	\N	190.00	cambios en el radiador	1	\N	3 meses	1	\N	aceptada	2026-06-06 02:28:12.736231+00	2026-06-07 02:23:58.986039+00	\N	\N	90.00	100.00	\N	1
12	21	2	\N	120.00	cambios en la bateria ver corriente	1	\N	3 meses	1	\N	rechazada	2026-06-06 02:29:16.098064+00	2026-06-07 02:23:58.986039+00	\N	\N	80.00	40.00	\N	1
13	20	1	\N	390.00	Cambio de batería, revisión eléctrica y limpieza de bornes	2 horas	20 minutos	6 meses	1	\N	aceptada	2026-06-06 02:45:27.714298+00	2026-06-07 02:07:59.4752+00	Batería 12V 75Ah premium	\N	90.00	300.00	Servicio incluye traslado	1
14	22	1	\N	200.00	mmmmmm	\N	\N	3 meses	1	\N	aceptada	2026-06-06 04:46:15.535454+00	2026-06-07 04:45:19.977576+00	\N	\N	70.00	130.00	\N	1
15	22	2	\N	500.00	mmmmmmm	1	\N	3 meses	1	\N	rechazada	2026-06-06 04:46:53.712358+00	2026-06-07 04:45:19.977576+00	\N	\N	200.00	300.00	\N	1
17	23	2	\N	700.00	jjjjjjj	\N	\N	3 meses	1	\N	aceptada	2026-06-06 04:51:42.664746+00	2026-06-07 04:50:58.507148+00	\N	\N	\N	\N	\N	1
16	23	1	\N	800.00	mmm	\N	\N	3 meses	1	\N	rechazada	2026-06-06 04:51:20.451335+00	2026-06-07 04:50:58.507148+00	\N	\N	\N	\N	\N	1
8	11	1	\N	520.00	Cambio de batería y prueba final	90 minutos	20 minutos	3 meses	2	Versión actualizada	aceptada	2026-06-06 01:05:06.924758+00	2026-06-08 01:05:24.947638+00	Batería 12V premium	Instalación, limpieza y prueba eléctrica	80.00	440.00	\N	1
\.


--
-- Data for Name: quotation_request_history; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_request_history (id, quotation_request_id, event_type, detail, actor_role, actor_user_id, created_at, tenant_id) FROM stdin;
1	9	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 00:54:54.371347+00	1
2	10	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 00:55:29.13107+00	1
3	10	cotizacion_enviada	Cotización enviada por el taller 1	workshop	1	2026-06-06 00:55:47.9876+00	1
4	10	cotizacion_aceptada	Se aceptó la cotización 7	client	1	2026-06-06 00:56:17.001897+00	1
5	11	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:04:49.85246+00	1
6	11	cotizacion_enviada	Cotización enviada por el taller 1	workshop	1	2026-06-06 01:05:06.924758+00	1
7	11	cotizacion_actualizada	Cotización 8 actualizada por el taller 1	workshop	1	2026-06-06 01:05:24.954738+00	1
8	12	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:06:51.229767+00	1
9	13	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:08:51.9727+00	1
10	14	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:13:45.220029+00	1
11	15	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:23:28.226348+00	1
12	16	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:33:04.874472+00	1
13	17	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:43:24.182363+00	1
14	18	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:43:32.139821+00	1
15	19	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 01:50:44.990709+00	1
16	19	cotizacion_enviada	Cotización enviada por el taller 1	workshop	1	2026-06-06 01:51:06.923984+00	1
17	19	cotizacion_enviada	Cotización enviada por el taller 2	workshop	2	2026-06-06 01:51:06.99353+00	1
18	19	cotizacion_aceptada	Se aceptó la cotización 9	client	1	2026-06-06 01:51:29.73268+00	1
19	20	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 02:07:59.476553+00	1
20	21	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 02:23:58.986645+00	1
21	21	cotizacion_enviada	Cotización enviada por el taller 1	workshop	1	2026-06-06 02:28:12.736231+00	1
22	21	cotizacion_enviada	Cotización enviada por el taller 2	workshop	2	2026-06-06 02:29:16.098064+00	1
23	21	cotizacion_aceptada	Se aceptó la cotización 11	client	1	2026-06-06 02:30:25.331136+00	1
24	20	cotizacion_enviada	Cotización enviada por el taller 1	workshop	1	2026-06-06 02:45:27.714298+00	1
25	20	cotizacion_actualizada	Cotización 13 actualizada por el taller 1	workshop	1	2026-06-06 02:45:36.499518+00	1
26	20	cotizacion_aceptada	Se aceptó la cotización 13	client	1	2026-06-06 02:45:51.039043+00	1
27	22	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 04:45:19.978712+00	1
28	22	cotizacion_enviada	Cotización enviada por el taller 1	workshop	1	2026-06-06 04:46:15.535454+00	1
29	22	cotizacion_enviada	Cotización enviada por el taller 2	workshop	2	2026-06-06 04:46:53.712358+00	1
30	22	cotizacion_aceptada	Se aceptó la cotización 14	client	1	2026-06-06 04:49:37.362939+00	1
31	23	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 04:50:58.508144+00	1
32	23	cotizacion_enviada	Cotización enviada por el taller 1	workshop	1	2026-06-06 04:51:20.451335+00	1
33	23	cotizacion_enviada	Cotización enviada por el taller 2	workshop	2	2026-06-06 04:51:42.664746+00	1
34	23	cotizacion_aceptada	Se aceptó la cotización 17	client	1	2026-06-06 04:52:03.797612+00	1
35	24	solicitud_creada	Solicitud de cotización creada y enviada a talleres compatibles	system	1	2026-06-06 05:01:36.273734+00	1
36	11	cotizacion_aceptada	Se aceptó la cotización 8	client	1	2026-06-06 05:08:15.031987+00	1
37	11	taller_seleccionado	El taller #1 fue seleccionado (oferta #8)	client	1	2026-06-06 05:08:15.040131+00	1
\.


--
-- Data for Name: quotation_request_workshops; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_request_workshops (id, quotation_request_id, workshop_id, status, notified_at, created_at, tenant_id) FROM stdin;
1	1	1	notificado	2026-06-05 21:35:09.840131+00	2026-06-05 21:35:09.840131+00	1
2	1	2	notificado	2026-06-05 21:35:09.846735+00	2026-06-05 21:35:09.846735+00	1
3	1	6	notificado	2026-06-05 21:35:09.85223+00	2026-06-05 21:35:09.85223+00	1
4	2	1	notificado	2026-06-05 23:06:56.392131+00	2026-06-05 23:06:56.392131+00	1
5	2	2	notificado	2026-06-05 23:06:56.40181+00	2026-06-05 23:06:56.40181+00	1
6	2	6	notificado	2026-06-05 23:06:56.409505+00	2026-06-05 23:06:56.409505+00	1
7	3	1	notificado	2026-06-05 23:08:07.203329+00	2026-06-05 23:08:07.203329+00	1
8	3	2	notificado	2026-06-05 23:08:07.206255+00	2026-06-05 23:08:07.206255+00	1
9	4	1	notificado	2026-06-06 00:06:36.275755+00	2026-06-06 00:06:36.275755+00	1
10	4	2	notificado	2026-06-06 00:06:36.279808+00	2026-06-06 00:06:36.279808+00	1
11	4	6	notificado	2026-06-06 00:06:36.284166+00	2026-06-06 00:06:36.284166+00	1
12	4	3	notificado	2026-06-06 00:06:36.287665+00	2026-06-06 00:06:36.287665+00	1
13	4	4	notificado	2026-06-06 00:06:36.291194+00	2026-06-06 00:06:36.291194+00	1
14	5	1	notificado	2026-06-06 00:12:58.307895+00	2026-06-06 00:12:58.307895+00	1
15	5	2	notificado	2026-06-06 00:12:58.310901+00	2026-06-06 00:12:58.310901+00	1
16	5	6	notificado	2026-06-06 00:12:58.313734+00	2026-06-06 00:12:58.313734+00	1
17	5	3	notificado	2026-06-06 00:12:58.316964+00	2026-06-06 00:12:58.316964+00	1
18	5	4	notificado	2026-06-06 00:12:58.319888+00	2026-06-06 00:12:58.319888+00	1
20	6	2	notificado	2026-06-06 00:19:14.070235+00	2026-06-06 00:19:14.070235+00	1
21	6	6	notificado	2026-06-06 00:19:14.074422+00	2026-06-06 00:19:14.074422+00	1
22	6	3	notificado	2026-06-06 00:19:14.078685+00	2026-06-06 00:19:14.078685+00	1
23	6	4	notificado	2026-06-06 00:19:14.082988+00	2026-06-06 00:19:14.082988+00	1
19	6	1	respondido	2026-06-06 00:19:14.065767+00	2026-06-06 00:19:14.065767+00	1
24	7	1	notificado	2026-06-06 00:42:41.70959+00	2026-06-06 00:42:41.70959+00	1
26	7	6	notificado	2026-06-06 00:42:41.71736+00	2026-06-06 00:42:41.71736+00	1
27	7	3	notificado	2026-06-06 00:42:41.720703+00	2026-06-06 00:42:41.720703+00	1
28	7	4	notificado	2026-06-06 00:42:41.723846+00	2026-06-06 00:42:41.723846+00	1
25	7	2	respondido	2026-06-06 00:42:41.713613+00	2026-06-06 00:42:41.713613+00	1
29	8	1	notificado	2026-06-06 00:45:53.427693+00	2026-06-06 00:45:53.427693+00	1
30	8	2	notificado	2026-06-06 00:45:53.431364+00	2026-06-06 00:45:53.431364+00	1
31	8	6	notificado	2026-06-06 00:45:53.433936+00	2026-06-06 00:45:53.433936+00	1
32	8	3	notificado	2026-06-06 00:45:53.436603+00	2026-06-06 00:45:53.436603+00	1
33	8	4	notificado	2026-06-06 00:45:53.43981+00	2026-06-06 00:45:53.43981+00	1
34	9	1	notificado	2026-06-06 00:54:54.376935+00	2026-06-06 00:54:54.376935+00	1
35	10	1	respondido	2026-06-06 00:55:29.134659+00	2026-06-06 00:55:29.134659+00	1
36	11	1	respondido	2026-06-06 01:04:49.85905+00	2026-06-06 01:04:49.85905+00	1
37	12	1	notificado	2026-06-06 01:06:51.235668+00	2026-06-06 01:06:51.235668+00	1
38	12	2	notificado	2026-06-06 01:06:51.23953+00	2026-06-06 01:06:51.23953+00	1
39	12	6	notificado	2026-06-06 01:06:51.243556+00	2026-06-06 01:06:51.243556+00	1
40	12	3	notificado	2026-06-06 01:06:51.247612+00	2026-06-06 01:06:51.247612+00	1
41	12	4	notificado	2026-06-06 01:06:51.252016+00	2026-06-06 01:06:51.252016+00	1
42	13	1	notificado	2026-06-06 01:08:51.976669+00	2026-06-06 01:08:51.976669+00	1
43	13	2	notificado	2026-06-06 01:08:51.97941+00	2026-06-06 01:08:51.97941+00	1
44	13	6	notificado	2026-06-06 01:08:51.982089+00	2026-06-06 01:08:51.982089+00	1
45	13	3	notificado	2026-06-06 01:08:51.984888+00	2026-06-06 01:08:51.984888+00	1
46	13	4	notificado	2026-06-06 01:08:51.987697+00	2026-06-06 01:08:51.987697+00	1
47	14	1	notificado	2026-06-06 01:13:45.224247+00	2026-06-06 01:13:45.224247+00	1
48	14	2	notificado	2026-06-06 01:13:45.227526+00	2026-06-06 01:13:45.227526+00	1
49	14	6	notificado	2026-06-06 01:13:45.230328+00	2026-06-06 01:13:45.230328+00	1
50	14	3	notificado	2026-06-06 01:13:45.233296+00	2026-06-06 01:13:45.233296+00	1
51	14	4	notificado	2026-06-06 01:13:45.235966+00	2026-06-06 01:13:45.235966+00	1
52	15	1	notificado	2026-06-06 01:23:28.231494+00	2026-06-06 01:23:28.231494+00	1
53	15	2	notificado	2026-06-06 01:23:28.235518+00	2026-06-06 01:23:28.235518+00	1
54	15	6	notificado	2026-06-06 01:23:28.238852+00	2026-06-06 01:23:28.238852+00	1
55	15	3	notificado	2026-06-06 01:23:28.241956+00	2026-06-06 01:23:28.241956+00	1
56	15	4	notificado	2026-06-06 01:23:28.245059+00	2026-06-06 01:23:28.245059+00	1
57	16	1	notificado	2026-06-06 01:33:04.880842+00	2026-06-06 01:33:04.880842+00	1
58	16	2	notificado	2026-06-06 01:33:04.884601+00	2026-06-06 01:33:04.884601+00	1
59	16	6	notificado	2026-06-06 01:33:04.88875+00	2026-06-06 01:33:04.88875+00	1
60	16	3	notificado	2026-06-06 01:33:04.89255+00	2026-06-06 01:33:04.89255+00	1
61	16	4	notificado	2026-06-06 01:33:04.896246+00	2026-06-06 01:33:04.896246+00	1
62	17	1	notificado	2026-06-06 01:43:24.189036+00	2026-06-06 01:43:24.189036+00	1
63	17	2	notificado	2026-06-06 01:43:24.19405+00	2026-06-06 01:43:24.19405+00	1
64	17	6	notificado	2026-06-06 01:43:24.198674+00	2026-06-06 01:43:24.198674+00	1
65	17	3	notificado	2026-06-06 01:43:24.202891+00	2026-06-06 01:43:24.202891+00	1
66	17	4	notificado	2026-06-06 01:43:24.20645+00	2026-06-06 01:43:24.20645+00	1
67	18	1	notificado	2026-06-06 01:43:32.144698+00	2026-06-06 01:43:32.144698+00	1
68	18	2	notificado	2026-06-06 01:43:32.147998+00	2026-06-06 01:43:32.147998+00	1
69	18	6	notificado	2026-06-06 01:43:32.151455+00	2026-06-06 01:43:32.151455+00	1
70	18	3	notificado	2026-06-06 01:43:32.154989+00	2026-06-06 01:43:32.154989+00	1
71	18	4	notificado	2026-06-06 01:43:32.159239+00	2026-06-06 01:43:32.159239+00	1
74	19	6	notificado	2026-06-06 01:50:45.001482+00	2026-06-06 01:50:45.001482+00	1
75	19	3	notificado	2026-06-06 01:50:45.005923+00	2026-06-06 01:50:45.005923+00	1
76	19	4	notificado	2026-06-06 01:50:45.009582+00	2026-06-06 01:50:45.009582+00	1
72	19	1	respondido	2026-06-06 01:50:44.995163+00	2026-06-06 01:50:44.995163+00	1
73	19	2	respondido	2026-06-06 01:50:44.998445+00	2026-06-06 01:50:44.998445+00	1
78	20	2	notificado	2026-06-06 02:07:59.488145+00	2026-06-06 02:07:59.488145+00	1
79	20	6	notificado	2026-06-06 02:07:59.492604+00	2026-06-06 02:07:59.492604+00	1
80	20	3	notificado	2026-06-06 02:07:59.496684+00	2026-06-06 02:07:59.496684+00	1
81	20	4	notificado	2026-06-06 02:07:59.500764+00	2026-06-06 02:07:59.500764+00	1
84	21	6	notificado	2026-06-06 02:23:59.001441+00	2026-06-06 02:23:59.001441+00	1
85	21	3	notificado	2026-06-06 02:23:59.004643+00	2026-06-06 02:23:59.004643+00	1
86	21	4	notificado	2026-06-06 02:23:59.007798+00	2026-06-06 02:23:59.007798+00	1
82	21	1	respondido	2026-06-06 02:23:58.993669+00	2026-06-06 02:23:58.993669+00	1
83	21	2	respondido	2026-06-06 02:23:58.99781+00	2026-06-06 02:23:58.99781+00	1
77	20	1	respondido	2026-06-06 02:07:59.483002+00	2026-06-06 02:07:59.483002+00	1
89	22	6	notificado	2026-06-06 04:45:19.998819+00	2026-06-06 04:45:19.998819+00	1
90	22	3	notificado	2026-06-06 04:45:20.003689+00	2026-06-06 04:45:20.003689+00	1
91	22	4	notificado	2026-06-06 04:45:20.008368+00	2026-06-06 04:45:20.008368+00	1
87	22	1	respondido	2026-06-06 04:45:19.988039+00	2026-06-06 04:45:19.988039+00	1
88	22	2	respondido	2026-06-06 04:45:19.994843+00	2026-06-06 04:45:19.994843+00	1
94	23	6	notificado	2026-06-06 04:50:58.525204+00	2026-06-06 04:50:58.525204+00	1
95	23	3	notificado	2026-06-06 04:50:58.529279+00	2026-06-06 04:50:58.529279+00	1
96	23	4	notificado	2026-06-06 04:50:58.532756+00	2026-06-06 04:50:58.532756+00	1
93	23	2	respondido	2026-06-06 04:50:58.520741+00	2026-06-06 04:50:58.520741+00	1
92	23	1	respondido	2026-06-06 04:50:58.515815+00	2026-06-06 04:50:58.515815+00	1
97	24	1	notificado	2026-06-06 05:01:36.280147+00	2026-06-06 05:01:36.280147+00	1
98	24	2	notificado	2026-06-06 05:01:36.285405+00	2026-06-06 05:01:36.285405+00	1
99	24	6	notificado	2026-06-06 05:01:36.289992+00	2026-06-06 05:01:36.289992+00	1
100	24	3	notificado	2026-06-06 05:01:36.294007+00	2026-06-06 05:01:36.294007+00	1
101	24	4	notificado	2026-06-06 05:01:36.297915+00	2026-06-06 05:01:36.297915+00	1
\.


--
-- Data for Name: quotation_requests; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.quotation_requests (id, emergency_id, client_id, status, requested_workshops_count, received_offers_count, selected_offer_id, requested_at, expires_at, created_at, updated_at, tenant_id) FROM stdin;
20	39	1	seleccionado	5	1	13	2026-06-06 02:07:59.476553+00	2026-06-07 02:07:59.4752+00	2026-06-06 02:07:59.476553+00	2026-06-07 04:26:14.432774+00	1
1	32	1	seleccionado	3	1	1	2026-06-05 21:35:09.8333+00	2026-06-06 21:35:09.83198+00	2026-06-05 21:35:09.8333+00	2026-06-07 04:26:14.432774+00	1
2	32	1	seleccionado	3	1	2	2026-06-05 23:06:56.383202+00	2026-06-06 23:06:56.38175+00	2026-06-05 23:06:56.383202+00	2026-06-07 04:26:14.432774+00	1
10	38	1	seleccionado	1	1	7	2026-06-06 00:55:29.13107+00	2026-06-09 00:55:29.130545+00	2026-06-06 00:55:29.13107+00	2026-06-07 04:26:14.432774+00	1
3	32	1	expirado	2	2	\N	2026-06-05 23:08:07.199991+00	2026-06-06 00:08:07.199521+00	2026-06-05 23:08:07.199991+00	2026-06-07 04:26:14.432774+00	1
6	38	1	expirado	5	1	\N	2026-06-06 00:19:14.061307+00	2026-06-07 00:19:14.060495+00	2026-06-06 00:19:14.061307+00	2026-06-07 04:26:14.432774+00	1
16	39	1	expirado	5	0	\N	2026-06-06 01:33:04.874472+00	2026-06-07 01:33:04.873842+00	2026-06-06 01:33:04.874472+00	2026-06-07 04:26:14.432774+00	1
17	37	1	expirado	5	0	\N	2026-06-06 01:43:24.182363+00	2026-06-07 01:43:24.181543+00	2026-06-06 01:43:24.182363+00	2026-06-07 04:26:14.432774+00	1
18	39	1	expirado	5	0	\N	2026-06-06 01:43:32.139821+00	2026-06-07 01:43:32.139194+00	2026-06-06 01:43:32.139821+00	2026-06-07 04:26:14.432774+00	1
9	38	1	expirado	1	0	\N	2026-06-06 00:54:54.371347+00	2026-06-07 00:54:54.37062+00	2026-06-06 00:54:54.371347+00	2026-06-07 04:26:14.432774+00	1
14	38	1	abierto	5	0	\N	2026-06-06 01:13:45.220029+00	2026-06-09 01:13:45.21941+00	2026-06-06 01:13:45.220029+00	2026-06-07 04:26:14.432774+00	1
24	39	1	abierto	5	0	\N	2026-06-06 05:01:36.273734+00	2026-06-07 05:01:36.272806+00	2026-06-06 05:01:36.273734+00	2026-06-07 04:26:14.432774+00	1
4	37	1	expirado	5	0	\N	2026-06-06 00:06:36.27115+00	2026-06-07 00:06:36.270538+00	2026-06-06 00:06:36.27115+00	2026-06-07 04:26:14.432774+00	1
5	38	1	expirado	5	0	\N	2026-06-06 00:12:58.303967+00	2026-06-07 00:12:58.303182+00	2026-06-06 00:12:58.303967+00	2026-06-07 04:26:14.432774+00	1
8	38	1	expirado	5	0	\N	2026-06-06 00:45:53.423719+00	2026-06-07 00:45:53.422964+00	2026-06-06 00:45:53.423719+00	2026-06-07 04:26:14.432774+00	1
12	38	1	expirado	5	0	\N	2026-06-06 01:06:51.229767+00	2026-06-07 01:06:51.228885+00	2026-06-06 01:06:51.229767+00	2026-06-07 04:26:14.432774+00	1
13	38	1	expirado	5	0	\N	2026-06-06 01:08:51.9727+00	2026-06-07 01:08:51.971985+00	2026-06-06 01:08:51.9727+00	2026-06-07 04:26:14.432774+00	1
15	39	1	expirado	5	0	\N	2026-06-06 01:23:28.226348+00	2026-06-07 01:23:28.225657+00	2026-06-06 01:23:28.226348+00	2026-06-07 04:26:14.432774+00	1
7	38	1	expirado	5	1	\N	2026-06-06 00:42:41.704888+00	2026-06-07 00:42:41.703994+00	2026-06-06 00:42:41.704888+00	2026-06-07 04:26:14.432774+00	1
11	38	1	seleccionado	1	1	8	2026-06-06 01:04:49.85246+00	2026-06-09 01:04:49.851452+00	2026-06-06 01:04:49.85246+00	2026-06-07 04:26:14.432774+00	1
19	37	1	seleccionado	5	2	9	2026-06-06 01:50:44.990709+00	2026-06-09 01:50:44.990249+00	2026-06-06 01:50:44.990709+00	2026-06-07 04:26:14.432774+00	1
21	39	1	seleccionado	5	2	11	2026-06-06 02:23:58.986645+00	2026-06-07 02:23:58.986039+00	2026-06-06 02:23:58.986645+00	2026-06-07 04:26:14.432774+00	1
22	36	1	seleccionado	5	2	14	2026-06-06 04:45:19.978712+00	2026-06-07 04:45:19.977576+00	2026-06-06 04:45:19.978712+00	2026-06-07 04:26:14.432774+00	1
23	36	1	seleccionado	5	2	17	2026-06-06 04:50:58.508144+00	2026-06-07 04:50:58.507148+00	2026-06-06 04:50:58.508144+00	2026-06-07 04:26:14.432774+00	1
\.


--
-- Data for Name: technicians; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.technicians (id, workshop_id, full_name, phone, email, specialty, status, created_at, updated_at, tenant_id, sucursal_id) FROM stdin;
2	1	brayan	75560845	brayan@gmail.com	Batería	disponible	2026-05-28 03:33:50.792493+00	2026-06-06 03:52:31.537249+00	1	\N
1	1	carlos ramirez	75560845	wilmafernandez1203@gmail.com	Batería	disponible	2026-05-28 03:28:15.396908+00	2026-06-06 05:34:02.812029+00	1	\N
3	1	leon	68876988	leon@gmail.com	Batería	disponible	2026-06-06 05:37:58.330495+00	2026-06-06 05:39:56.853115+00	1	\N
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.tenants (id, nombre, descripcion, estado, created_at, updated_at) FROM stdin;
1	Tenant Principal	Tenant principal del sistema	activo	2026-06-06 06:03:06.428667+00	2026-06-06 06:03:06.428667+00
2	Mecánicos Express	Red de talleres Mecánicos Express	activo	2026-06-06 12:03:14.245529+00	2026-06-06 12:03:14.245529+00
3	Auxilio Norte	Red de asistencia vehicular Auxilio Norte	activo	2026-06-06 12:03:14.297442+00	2026-06-06 12:03:14.297442+00
\.


--
-- Data for Name: vehicles; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.vehicles (id, client_id, brand, model, year, plate, color, is_primary, photo_path, photo_url, created_at, tenant_id) FROM stdin;
1	1	Hilux	RTXL	2024	2906SEX	negro	t	\N	\N	2026-05-28 02:04:00.211922+00	1
2	1	Toyots	Corolls	2026	5678TYV	blanco	t	\N	\N	2026-05-28 02:04:32.596331+00	1
\.


--
-- Data for Name: workshop_registrations; Type: TABLE DATA; Schema: public; Owner: diagramador
--

COPY public.workshop_registrations (id, workshop_name, contact_name, phone, email, zone, specialty, approval_status, password_hash, latitude, longitude, timezone, utc_offset_minutes, created_at, availability_status, tenant_id, sucursal_id) FROM stdin;
1	ElectroCar	diego toledo	75560845	diego@gmail.com	zona centro	Batería	activo	b2f4d07c3f3564fb0c1baa6d2ad95cf6$0be5b7ce3122da525f9e8e35792736ccdeb3d0b141fc180ca38565b1ebe5a32c	-17.778684693540267	-63.20420698292684	America/La_Paz	-240	2026-05-28 00:47:44.218074+00	disponible	1	\N
3	AutoVolt	miguel	75560845	miguel@gmail.com	zona norte	Batería	activo	baeaff841e099929d31806ccff4c6510$c6649f814c8b96b6e21bbaf918f12c40b94c13025adf507d40bc13a6720dd1d3	-17.743781861322226	-63.16134433452514	America/La_Paz	-240	2026-05-28 01:10:48.809729+00	disponible	1	\N
4	Doctor Batería	roy barrero	75560845	roy@gmail.com	zona sur	Batería	activo	b0ec3e7676754556237fa1a7c2da8c5b$f2a12d98019884ecbf3aff2b00c8dbe226d09dfcc0f5d8cbce7e56ee7c04dda1	-17.854678965874708	-63.164264127318255	America/La_Paz	-240	2026-05-28 01:13:43.14712+00	disponible	1	\N
5	Taller Voltio	cristian huari	75560845	cristian@gmail.com	zona este	Batería	activo	75f61fd22602ffdaaa7fa629ef6ddfb1$2a23d0a1060074be3a56f7f6f98049694eb656c5762aba50121f51b4d262e275	-17.86342031339141	-63.080873263603266	America/La_Paz	-240	2026-05-28 01:18:40.014394+00	disponible	1	\N
6	Baterías del Oeste	leonardo gonzales	75560845	leonardo@gmail.com	zona oeste	Batería	activo	7afbc0787c8bdfa2e4d29907e1807662$b2fbb027378f696fe4f847b355283ec7be68f359fe84d7b9afc406406781ecb6	-17.768304469150404	-63.227341045527595	America/La_Paz	-240	2026-05-28 01:22:37.55459+00	disponible	1	\N
2	PowerAuto	alex	75560845	alex@gmail.com	zona centro	Batería	activo	1551ccb56a9a7fe9d231e959f6af6d9a$28a94bb19221552fce053dca86764b0367d0203d39208ec89fac3c94d2b08fe3	-17.76307326153082	-63.19202882502281	America/La_Paz	-240	2026-05-28 01:07:19.94188+00	disponible	1	\N
\.


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.clients_id_seq', 5, true);


--
-- Name: device_fcm_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.device_fcm_tokens_id_seq', 122, true);


--
-- Name: emergency_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_assignments_id_seq', 13, true);


--
-- Name: emergency_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_reports_id_seq', 40, true);


--
-- Name: emergency_status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_status_history_id_seq', 109, true);


--
-- Name: emergency_tracking_points_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.emergency_tracking_points_id_seq', 1, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.notifications_id_seq', 108, true);


--
-- Name: quotation_offers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_offers_id_seq', 17, true);


--
-- Name: quotation_request_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_request_history_id_seq', 37, true);


--
-- Name: quotation_request_workshops_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_request_workshops_id_seq', 101, true);


--
-- Name: quotation_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.quotation_requests_id_seq', 24, true);


--
-- Name: technicians_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.technicians_id_seq', 3, true);


--
-- Name: tenants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.tenants_id_seq', 3, true);


--
-- Name: vehicles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.vehicles_id_seq', 2, true);


--
-- Name: workshop_registrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: diagramador
--

SELECT pg_catalog.setval('public.workshop_registrations_id_seq', 6, true);


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
-- Name: technicians technicians_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.technicians
    ADD CONSTRAINT technicians_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


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
-- Name: emergency_reports_local_id_key; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE UNIQUE INDEX emergency_reports_local_id_key ON public.emergency_reports USING btree (local_id) WHERE (local_id IS NOT NULL);


--
-- Name: idx_clients_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_clients_tenant_id ON public.clients USING btree (tenant_id);


--
-- Name: idx_device_fcm_tokens_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_device_fcm_tokens_tenant_id ON public.device_fcm_tokens USING btree (tenant_id);


--
-- Name: idx_emergency_assignments_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_emergency_assignments_tenant_id ON public.emergency_assignments USING btree (tenant_id);


--
-- Name: idx_emergency_reports_sucursal_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_emergency_reports_sucursal_id ON public.emergency_reports USING btree (sucursal_id);


--
-- Name: idx_emergency_reports_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_emergency_reports_tenant_id ON public.emergency_reports USING btree (tenant_id);


--
-- Name: idx_emergency_status_history_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_emergency_status_history_tenant_id ON public.emergency_status_history USING btree (tenant_id);


--
-- Name: idx_emergency_tracking_points_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_emergency_tracking_points_tenant_id ON public.emergency_tracking_points USING btree (tenant_id);


--
-- Name: idx_notifications_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_notifications_tenant_id ON public.notifications USING btree (tenant_id);


--
-- Name: idx_notifications_user_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: idx_quotation_offers_quotation_request_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_offers_quotation_request_id ON public.quotation_offers USING btree (quotation_request_id);


--
-- Name: idx_quotation_offers_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_offers_tenant_id ON public.quotation_offers USING btree (tenant_id);


--
-- Name: idx_quotation_offers_workshop_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_offers_workshop_id ON public.quotation_offers USING btree (workshop_id);


--
-- Name: idx_quotation_request_history_request_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_request_history_request_id ON public.quotation_request_history USING btree (quotation_request_id);


--
-- Name: idx_quotation_request_history_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_request_history_tenant_id ON public.quotation_request_history USING btree (tenant_id);


--
-- Name: idx_quotation_request_workshops_quotation_request_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_request_workshops_quotation_request_id ON public.quotation_request_workshops USING btree (quotation_request_id);


--
-- Name: idx_quotation_request_workshops_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_request_workshops_tenant_id ON public.quotation_request_workshops USING btree (tenant_id);


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
-- Name: idx_quotation_requests_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_quotation_requests_tenant_id ON public.quotation_requests USING btree (tenant_id);


--
-- Name: idx_technicians_sucursal_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_technicians_sucursal_id ON public.technicians USING btree (sucursal_id);


--
-- Name: idx_technicians_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_technicians_tenant_id ON public.technicians USING btree (tenant_id);


--
-- Name: idx_vehicles_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_vehicles_tenant_id ON public.vehicles USING btree (tenant_id);


--
-- Name: idx_workshop_registrations_sucursal_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_workshop_registrations_sucursal_id ON public.workshop_registrations USING btree (sucursal_id);


--
-- Name: idx_workshop_registrations_tenant_id; Type: INDEX; Schema: public; Owner: diagramador
--

CREATE INDEX idx_workshop_registrations_tenant_id ON public.workshop_registrations USING btree (tenant_id);


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
-- Name: technicians technicians_workshop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.technicians
    ADD CONSTRAINT technicians_workshop_id_fkey FOREIGN KEY (workshop_id) REFERENCES public.workshop_registrations(id) ON DELETE CASCADE;


--
-- Name: vehicles vehicles_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: diagramador
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 9APdWqnRpCuhOBZnJdn04DUnTd46OgQfHf2Eeu0LJkTD6njcB2Rd4d9kIEVYQtK

