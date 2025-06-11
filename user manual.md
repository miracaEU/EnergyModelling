# Energy Mapping & Power Flow: Setup to Execution Guide

## 1. Environment Setup
You can set up your environment using either Conda (recommended) or pip.

### Option A: Conda Virtual Environment
1. Open Anaconda Prompt.

2. Run the following command to create a conda virtual env:
   ```bash
   conda env create -f environment.yaml
   ``` 
3. Activate the environment:   
   ```bash
   conda activate miraca
   ```
Or create separate environment based on channel and use case from "envs" folder:
- Default channel:
   ```bash
   conda env create -f envs/environment-default.yaml
   ```
- Conda-forge
   ```bash
   conda env create -f envs/environment-conda-forge.yaml
   ```
- Jupyter-notebook
   ```bash
   conda env create -f envs/environment-jupyter.yaml 
   ```
Activate virtual env by running:   
   ```bash
   conda activate miraca_energy_env
   ```
      
### Option B: Pip Installation
1. Open a terminal or command prompt.

2. Create a virtual environment:
   ```bash
   python -m venv miraca_energy_env
   ``` 
3. Activate the virtual environment:

    - #### Windows:
        ```bash
        miraca_energy_env\Scripts\activate
        ```

    - #### Mac/Linux:
        ```bash
        source miraca_energy_env/bin/activate
        ```

4. Install dependencies from requirements.txt:
    
    ```bash
    pip install -r requirements.txt
    ```

## 2. Run Jupyter Notebook or Main Program 

### Option 1: Prepare Kernel and Run Juypter Notebook
1. Prepare the kernel by running the following command in the terminal:

    ```bash
    python -m ipykernel install --user --name=miraca_energy_env --display-name "Python (miraca_energy_env)"	     
    ```
2. Start Jupyter Notebook by executing:

    ```bash
    jupyter notebook	     
    ```

### Option 2: Run the Main Program from the Terminal
- Execute the Python script within the virtual environment:

    ```bash
    py main_program.py
    ```
    or 
    ```bash
    python main_program.py
    ```
## 3. Configurable Options and Required Input Parameters

### 1. Country Selection
- Available European countries:

    ```
    Available EU countries: ['Albania', 'Austria', 'Belgium', 'Bosnia and Herzegovina', 'Bulgaria', 'Croatia',
    'Czech Republic', 'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Ireland', 
    'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Montenegro', 'Netherlands', 'North Macedonia', 'Norway',
    'Poland', 'Portugal', 'Romania', 'Serbia', 'Slovakia', 'Slovenia', 'Spain', 'Sweden', 'Switzerland',
    'Ukraine', 'United Kingdom', 'Kosovo', 'Moldova']
    ```

- Input the full name(s) or code(s) of the country/countries: 
    ```bash
    Enter country or countries (e.g., 'Slovenia, Austria' or 'SI, AT'). You can use full names or country codes. 
    Type 'all' or 'EU' to process all available options: Slovenia, Austria [Enter]
    ```
- Output:
    ```bash    
    Countries to filter: ['SI', 'AT']
    Countries to filter (ISO codes): ['SI', 'AT']
    Import completed!
    ```
### 2. Time Interval Selection
- Select time interval:     
    ```bash
    Enter the start time (default: '2015-01-01 00:00:00'): [Enter] or 2015-01-01 00:00:00
    Enter the end time (default: '2015-02-01 01:00:00'): [Enter] or 2015-02-01 01:00:00
    ```
- Output:
    ```bash
    Start time: 2015-01-01 00:00:00
    End time: 2015-02-01 01:00:00
    2015
    ```
### 3. Mapping Power Plants (Supply) 
- Prompt:    
    ```bash
    Do you want to distribute plants to their closest bus (without voltage optimization)? (yes/no):
    ```
- If **yes**, each plant will be mapped to the nearest bus without voltage optimization.
- If **no**, plants will instead be assigned to the **lowest voltage bus** within the same region. If no bus is available within the region, the closest bus will be selected.

### 4. Mapping of Consumers (Demand)
- Prompt:    
    ```bash
    Do you want to distribute loads evenly within NUTS regions (without voltage optimization)? (yes/no):
    ```
- If **yes**, consumer loads will be evenly distributed within NUTS regions without voltage optimization.
- If **no**, loads will be assigned to the **lowest voltage bus** within the region. If no bus is available within the region, the closest bus will be selected.

### 5. Plotting Results

#### 5.1 Plotting Connections between Buses and Consumers/Generators:
- Prompt:    
    ```bash
    Do you want to plot connections between buses and load/gen? (yes/no):
    ```
**Type yes or no. If yes, the following plots will be generated:**

- Processed NUTS Regions
- Connections Between NUTS Centroids (Loads) and Buses
- Connections Between Generators and Buses

#### 5.2 Plotting Generation and Consumption Results:
- Prompt:
    ```bash
    Do you want to plot generation and consumption results? (yes/no):
    ```
**Type yes or no. If yes, the following plots will be generated:**

- Capacities from DC OPF results
- Installed capacities per bus
- Installed capacities at real locations

## 4. Notes

- If using Conda, ensure Conda is installed and updated before running commands.
- If using pip, ensure Python and pip are up-to-date before installing dependencies.
- Use appropriate country names or codes without quotation marks (""), e.g., UK instead of "UK".
- If encountering errors, check the logs and verify that dependencies are correctly installed.
