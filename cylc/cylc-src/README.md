# Cylc workflow setup and management guide
---

Step-by-step instructions for setting up, running, and monitoring Cylc workflows on NCI Gadi.

A more comprehensive set of instructions can be found at the [ACCESS-HIVE DOCS](https://docs.access-hive.org.au/models/run_a_model/rose_cylc/#launch-are-vdi-desktop).


### 1. "Persistent Sessions"


##### 1.1 Start a persistent session

Start a persistent session so it does not shutdown Cylc on terminal session logout. 
More on "persistent sessions" can be found [here](https://opus.nci.org.au/spaces/Help/pages/241926895/Persistent+Sessions).

```bash
persistent-sessions start -p <project-id> <arbitrary-session-name>
```

##### 1.1 List and connect to sessions

```bash
# List running sessions
persistent-sessions list -p <project-id>

# SSH into your session
ssh <arbitrary-session-name>.<user-id>.<project-id>.ps.gadi.nci.org.au
```


### 2. Pre-execution requirements 

##### 2.1 Required environment file

The following environment variables are required to be set on a user-by-user case. The required environment variables must be stored and saved on a file created at the user home directory e.g., `$HOME/.my_cylc.env`. Following is the content expected:

```bash
## -- USER-SPECIFIC: 
export MY_CYLC_GITREPO_DIR="<path-to-cloned-repo>/coastal-commons-forecast"
export MY_TASK_SCRIPT_DIR="$MY_CYLC_GITREPO_DIR/task"

## -- CYLC-SPECIFIC:
## workflow directories
export CYLC_WORKFLOW_SOURCE_DIR="$MY_CYLC_GITREPO_DIR/cylc/cylc-src"
export CYLC_WORKFLOW_SOURCE_DIR_ROSES="$MY_CYLC_GITREPO_DIR/cylc/roses"
```

##### 2.2 Required modules

The following modules are required to be able to work with Cylc.

**NOTE:** *You must be a member of project `hr22`, if you are not already please [request to join](https://my.nci.org.au/mancini/project/hr22)*


```bash
module use /g/data/hr22/modulefiles
module load cylc/8.6.4
```

##### 2.2 Required codebase

The shared, community code repository for the Coastal Commons Forecast workflow are available on GitHub at [coastal-commons-forecast](https://github.com/ACCESS-Community-Hub/coastal-commons-forecast)

Pick a directory at you local workstation to store the codebase, and clone it as follow:

```bash
git clone git@github.com:ACCESS-Community-Hub/coastal-commons-forecast.git
```

### 2. Running a forecast workflow


The `global-workflow` consists of a simple "demo" workflow set to execute a chain of two tasks:

- `download_ecmwf-ifs_global`: download the global atmospheric `ecmwf-ifs` model / product outputs; 

- `subset_ecmwf-ifs_global_to_aus`: subsets the global atmospheric `ecmwf-ifs` model / product outputs to a region surrounding Australia. 

**Note:** `subset_ecmwf-ifs_global_to_aus` depends on, and will only be triggered, upon successful completion of the *upstream parent* trask `subset_ecmwf-ifs_global_to_aus`.



##### 2.1 Execute "global-worflow"

Following is a step-by-step to run the existing "demo" workflow `global-worflow`.

```bash
# Install workflow
cylc install global-workflow

# Validate workflow configuration
cylc validate global-workflow

# Execute the workflow
cylc play global-workflow
```


##### 2.1 Monitoring "global-worflow"

Cylc provides a Terminal User Interface `tui` allowing users to track job statuses, view logs, and control workflow execution directly from the command line with minimal overhead.: 

```bash
cylc tui global-workflow
```


## Additional Resources

- [NCI Persistent Sessions](https://opus.nci.org.au/spaces/Help/pages/241926895/Persistent+Sessions)
- [ARE VDI Sessions for Cylc Jobs](https://opus.nci.org.au/spaces/DAE/pages/252674220/ARE+VDI+Sessions+for+Cylc+Jobs)
