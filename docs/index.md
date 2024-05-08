# Crowd Behavior Study via CARLA

### Abstract
This study aims to evaluate the physiological impacts of interacting with drivers exhibiting varying behaviors on an individual operating a vehicle within a simulated environment. We will collect biometric data from the individual. In this way, we will assess how stressed an individual is in varying conditions. Specific behaviors will be modeled in the simulation, including aggressive drivers whose presence is hypothesized to increase the stress level of the individual driving. Behaviors of aggressive drivers will include but are not limited to, speeding, frequent lane changes, tailgating, etc. The primary objective is to assess whether and how the social dynamics of road interactions influence a driver’s physiological responses. Furthermore, this research will investigate how environmental factors such as the weather and the speed limit will separately and in combination with one another affect the physiological responses of the driver. The findings are expected to provide insights into how different driving scenarios can be stress-inducing, thereby affecting the overall traffic flow and safety of the system.

* * *

### Proposed Timeline
![Proposed Timeline](/CBSvC/assets/images/Timeline2.jpg)


### Literature Review

Our background review focuses on evaluating driver behavior, driver monitoring with biometrics, and. We researched studies aimed at enhancing road safety, improving accident prevention technologies, and aspects of human-driven and autonomous vehicle interactions that were relevant to our subject matter. The key findings are as follows:

#### Evaluating Driver Behavior in Varied Driving Scenarios
Studying driver behavior under varying conditions in a simulated environment is an important aspect of our research. Xu et al. [^1] analyzes the differences in the responses of novice and experienced drivers to visually overwhelming traffic violations by observing their eye movements. Factors such as varied lighting and weather conditions however were not explored. Another study assessed the impact of repeated frustrating events on driver aggression among university students [^2]. The results show that the stress from such events could enhance aggressive behaviors. However, the study did not consider the influence of other aggressive drivers on the ego vehicle. Our research goal is thus to introduce new variables in driving scenarios and also evaluate how surrounding drivers can affect driving behavior.

#### Leveraging Biometrics for Effective Driver Monitoring
Montanaro et al. [^3] introduce a novel driver monitoring system that combines behavioral and physiological data to assess drivers' state. Biometric sensors and facial recognition are used to quantify the driver’s sleepiness and fatigue levels. The system is effective in measuring fatigue but has two key drawbacks: dependence on consistent lighting and delays in processing sensor data in real time.

#### Simulating Complex Driving Scenarios with CARLA
CARLA can be used to simulate complex driving scenarios incorporating several variables such as weather conditions and the behavior of drivers in surrounding traffic. A recent study [^4] shows promising results in using CARLA to simulate diverse weather and traffic conditions, by extending CARLA’s inbuilt functionality with Probabilistic Graphical Models (PGMs). This framework does have a limited number of configurable parameters and this is an aspect we aim to improve upon.

[^1]: Xu, J., Guo, K., & Sun, P. Z. (2022). Driving performance under violations of traffic rules: Novice vs. experienced drivers. IEEE Transactions on Intelligent Vehicles, 7(4), 908-917.

[^2]: Abou-Zeid, M., Kaysi, I., & Al-Naghi, H. (2011, September). Measuring aggressive driving behavior using a driving simulator: An exploratory study. In 3rd international conference on road safety and simulation (Vol. 2011, pp. 1-19).

[^3]: Montanaro, S., Santoro, E., Landolfi, E., Pascucci, F., & Natale, C. (2022, July). A hybrid approach based on behavioural and physiological data for driver monitoring systems. In 2022 European Control Conference (ECC) (pp. 775-782). IEEE.

[^4]: Malik, S., Khan, M. A., Aadam, El-Sayed, H., Iqbal, F., Khan, J., & Ullah, O. (2023). CARLA+: An Evolution of the CARLA Simulator for Complex Environment Using a Probabilistic Graphical Model. Drones, 7(2), 111.

* * *

### Preliminary Design
![System Design](/CBSvC/assets/images/system_design.png)

This project utilizes a Logitech G920 steering wheel and pedals control for driver input. Biometrics data is provided by a Zephyr bioharness strapped to the driver.

Custom traffic scenarios are constructed in CARLA. These scenarios spawn traffic vehicles with custom behavior, such as aggressive driving, and in different weather conditions.

The idea is to evaluate the driver's reaction to various driving scenarios by analyzing data from the ego vehicle and the driver's biometrics.

* * *

### Team Member Responsibilities
* **Aniruddha Chaki**
  - Data collection configuration
  - Test driving the simulation
  - Setting up simulation constraints
* **Puya Fard**
  - Data collection configuration
  - Test driving the simulation
  - Setting up simulation constraints
* **Ruchi Patel**
  - Documentation of data collection from simulation
  - Test driving of the simulation
  - Organization of the collected data to be analyzed.
* **Sauryadeep Pal**
  - Research and Design algorithms for the analysis required on collected data
  - Test driving the simulation
  - Setting up simulation constraints
* **Yasamin Moghaddas**
  - Research and Design algorithms for the analysis required on collected data
  - Test driving the simulation
  - Setting up simulation constraints

  * * *

### References
