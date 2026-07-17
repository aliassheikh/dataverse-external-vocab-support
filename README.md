# Dataverse External Vocabulary Management

Dataverse supports the use of third-party vocabulary and persistent identifier (PID) services through a generic external vocabulary support mechanism that allows service-specific scripts, and field-specific json configurations added via a Dataverse setting that allows specification of how fields in Dataverse metadatablocks are to be associated with specific services and vocabularies.

For example, instead of a plain text type in, one could select a term from multiple vocabularies:

Select a vocabulary

![Input2](https://github.com/user-attachments/assets/e984acc4-de04-49f7-8397-a7f2c4fc70f5)

and then a term

![Input3](https://github.com/user-attachments/assets/de48f382-4d74-4e75-aa29-a76853e88eba)

and have them displayed as a link to the remote site defining the term:

![Display2](https://github.com/user-attachments/assets/27aab9fe-c876-4ab6-8d74-eb6cc29274c4)

Or, with [enhancements added in Dataverse 6.4](https://github.com/IQSS/dataverse/pull/10712), one can replace the four author related fields with selectors for [ORCID](https://orcid.org) (people) and [ROR](https://ror.org) (organizations)

![Input1](https://github.com/user-attachments/assets/b0f724e1-952b-4d48-8f89-8f046d797ce8)

which would display as entries with icons that link to the definition pages.

![Display1](https://github.com/user-attachments/assets/67fd166e-855b-4044-8dfd-d2ae0ccbfed5)

and can still support entering info for people/organizations who do not have ORCID or ROR entries.

Display can also be graphical, as in displaying [Local Contexts](https://localcontexts.org/) Notices and Labels

![image](https://github.com/user-attachments/assets/87aab5b1-6aca-49b1-8f7a-1e253932650d)

## Repository Contents

This repository is organized into **services**, where each service (e.g., `person-or-org`, `publications`, `geonames`) contains its own scripts, configurations, and documentation.

- `services/`: Contains the logic and configuration for each vocabulary/PID service, along with service-specific examples and documentation.
- `dist/`: A centralized directory for web server access, containing symlinks to all production-ready scripts, internationalization files, and images.
- `scripts/`: Deployment and configuration management tools.

It also contains a [JSON Schema that can be used to validate configuration files](services/person-or-org/configs/CVocConf.schema.json).

## Scripts in Production

The following services are being used in production (or testing) at one or more Dataverse sites:

* **ORCID and ROR for Person/Organization** - see [services/person-or-org/README.md](services/person-or-org/README.md)
* **OntoPortal for Dataset keywords** - see [services/ontoportal/](services/ontoportal/)
* **Integration with [Local Contexts](https://localcontexts.org)** - see [services/local-contexts/README.md](services/local-contexts/README.md)
* **Geonames for geographical locations** - see [services/geonames/](services/geonames/)

## Deployment

We provide an interactive deployment script to simplify the process of configuring and installing CVOC scripts.

### 1. Initialize the Distribution Directory
Populate the `dist/` directory with symlinks to the service files. This directory can then be linked to your web server (e.g., Apache or Nginx).

**Using Node.js:**
```bash
node scripts/deploy.js link
```

**Using Python:**
```bash
python scripts/deploy.py link
```

### 2. Compose and Customize Configuration
Use the interactive tool to select the services you want to deploy, combine their configurations, and optionally rewrite `js-url` to point to your local web server.

**Using Node.js:**
```bash
node scripts/deploy.js compose
```

**Using Python:**
```bash
python scripts/deploy.py compose
```

### 3. Update Dataverse Settings
Upload the generated `CVocConf.json` directly to your Dataverse instance.

**Using Node.js:**
```bash
node scripts/deploy.js updateDataverse
```

**Using Python:**
```bash
python scripts/deploy.py updateDataverse
```

The script will prompt for your Dataverse URL and an optional unblock key if your API is restricted. Upon success, your new configuration will be active.

Note: Individual scripts may also require specific metadata blocks or other configuration. Please review the instructions for each service you use.

---

## How It All Works

The basic idea of the Dataverse External Vocabulary mechanism is to simplify adding and displaying controlled terms and PIDs as metadata. As far as Dataverse is concerned, all that is happening is that a term or PID URI is being entered into a text field and Dataverse then stores and displays the term/PID URI. The interesting part is that a JavaScript is taking over Dataverse's text input and text display to instead provide support such as a type-ahead lookup from a vocabulary/PID service and, on the diplay side, displaying the human-readable name of associated with the term/PID, and potentially additional metadata about the term/PID, rather than the raw URI.

The scripts know which fields to manage based on some invisible data-cvoc-* attributes Dataverse adds to the page's HTML. Dataverse has a flexible configuration mechanism to allow admins to specify which fields should be associated with which scripts, but, in other repositories, these associations could be static. For example, [this simple static example page](services/person-or-org/examples/staticOrcidAndRorExample.html) shows the ORCID and ROR scripts associated with two input and two display fields. You can look at the page source to see the additional attributes in the HTML that make this work.

There's more of course. When a repository already has separate subfields for names and identifiers, scripts can be written to fill in both. If the underlying vocabulary/PID service supports multiple vocabularies, or has an advanced search mechanism, the scipts can be written to let you select which vocabulary to use or provide an advanced search interface. If there's a field where you want to be able to handle free text as well as controlled terms/PIDs, scripts can support that as well. Dataverse also includes a mechanism to allow metadata about the terms/PIDs to be captured, making it possible to provide internationalization for search (i.e. allowing search in your language for a term), include organization acronyms in exported metadata formats, etc. Fortunately, most of this complexity is handled by script/config example developers and Dataverse admins just need to select which ones to install.

For further details, see [James D. Myers, & Vyacheslav Tykhonov. (2023). A Plug-in Approach to Controlled Vocabulary Support in Dataverse.](https://doi.org/10.5281/zenodo.8133723)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8133723.svg)](https://doi.org/10.5281/zenodo.8133723)


