# Crowd Behavior Study via CARLA

### Abstract
This study aims to evaluate the physiological impacts of interacting with drivers exhibiting varying behaviors on an individual operating a vehicle within a simulated environment. We will collect biometric data from the individual. In this way, we will assess how stressed an individual is in varying conditions. Specific behaviors will be modeled in the simulation, including aggressive drivers whose presence is hypothesized to increase the stress level of the individual driving. Behaviors of aggressive drivers will include but are not limited to, speeding, frequent lane changes, tailgating, etc. The primary objective is to assess whether and how the social dynamics of road interactions influence a driver’s physiological responses. Furthermore, this research will investigate how environmental factors such as the weather and the speed limit will separately and in combination with one another affect the physiological responses of the driver. The findings are expected to provide insights into how different driving scenarios can be stress-inducing, thereby affecting the overall traffic flow and safety of the system.

* * *

### Project Timeline
![Project Timeline](/CBSvC/assets/images/complete_timeline.png)


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

### System Design and Preliminary Results
#### Methodology
![System Design](/CBSvC/assets/images/system_design.png)

This project utilizes a Logitech G920 steering wheel and pedals control for driver input. Biometrics data is provided by a Zephyr bioharness strapped to the driver.

Custom traffic scenarios are constructed in CARLA. These scenarios spawn traffic vehicles with custom behavior, such as aggressive driving, and in different weather conditions. We define five custom scenarios:

1. **Default Driving**
<br>Driving in clear sunny weather with normal traffic behavior.
2. **Night Driving**
<br>Driving in clear night weather with normal traffic behavior.
3. **Surrounded by Distracted Drivers**
<br>Driving in clear sunny weather but some surrounding drivers ignore traffic lights and stop signs.
4. **Surrounded by Overspeeding Drivers**
<br>Driving in clear sunny weather but some surrounding drivers overspeed.
5. **Driving in Congested Traffic**
<br>Driving in clear sunny weather through areas of traffic congestion.

The idea is to evaluate the driver's reaction to various driving scenarios by analyzing data from the ego vehicle and the driver's biometrics. Data collection consists of making each participant drive each scenario for 10 minutes.

#### Sample Results
![Clear Day Reaction](/CBSvC/assets/images/driving_clear_day.png)<br>
*Baseline result of driver's reaction in a clear day driving scenario.*



![Clear Night Reaction](/CBSvC/assets/images/driving_clear_night.png)<br>
*Driver's reaction in a clear day driving scenario. The driver is more cautious as can be observed from the frequent braking, possibly due to lower visibility at night.*



![Running Red Light Reaction](/CBSvC/assets/images/running_red_light_reaction.png)<br>
*Driver's reaction to witnessing a vehicle running a red light. The driver has to brake abruptly and stays still for a few moments due to shock. Upon resuming, they drive cautiously at half speed likely because they want to avoid more incidents.*



![Overspeeding Reaction](/CBSvC/assets/images/overspeeding_reaction.png)<br>
*Driver's reaction to witnessing a vehicle overspeeding. The driver rapidly decelerates and does not move for while. This could be a natural side effect of the stress induced by the scenario upon the driver.*



![Ignoring Signs Reaction](/CBSvC/assets/images/ignoring_signs_reaction.png)<br>
*Driver's reaction to witnessing a vehicle ignoring a stop sign. There is rapid deceleration from 60 kph to a sustained 0 kph for several timestamps. The driver accelerates once more but never reaches 60 kph again. This could be due to the driver driving more cautiously around a vehicle that violates traffic rules.*



![Driving in Congested Traffic](/CBSvC/assets/images/driving_congested.png)<br>
*Driver tends to brake a lot more in congested traffic. Post-congestion, the driver tends to accelerate to higher speeds possibly due to frustation induced by the congestion.*

* * *

### Final Results
#### Overall Data Summary
![Overall Summary](/CBSvC/assets/images/overall_summary.png)
*Summary of vehicle speed, driver heart rate, and driver breathing rate data from all participants, across all scenarios*

#### Data Clustering Results
![Default](/CBSvC/assets/images/Default_boxplot.png)
*Default driving*



![Night](/CBSvC/assets/images/Night_boxplot.png)
*Night driving*



![Distracted](/CBSvC/assets/images/Distracted_boxpolot.png)
*Surrounded by distracted drivers*



![Overspeeding](/CBSvC/assets/images/Overspeeding_boxplot.png)
*Surrounded by overspeeding drivers*



![Congested](/CBSvC/assets/images/Congested_boxplot.png)
*Driving in Congested Traffic*



#### Summary of Clustering Results
We used data clustering to conduct a behavioral analysis of the collected data. The clustering algorithm used was DBSCAN and each data sample in the input data was a three element vector consisting of the vehicle speed, driver's heart rate, and driver's breathing rate.

For Default versus when the surrounding vehicles are overspeeding, the heart rate increases from an average of 82 bpm in the default scenario to 86 bpm when surrounding vehicles are overspeeding. This suggests a slight elevation  in stress levels possibly due to the increased pace and potential perceived risk of the driving environment.

For default versus when the surrounding vehicles are distracted, an even larger increase in heart rate is observed, from 82 bpm to 88 bpm. This indicates that drivers may experience higher stress or anxiety when nearby drivers are distracted, possibly due to the unpredictability and increased perceived danger this scenario introduces.

For default versus congestion, there’s a minor increase in average speed from 20 km/h to 17 km/h in congestion. This reduction in speed is typical of congested traffic conditions and reflects the restricted movement and potential frustration or stress associated with such environments.

For default versus night driving, night driving results in a significant tendency to overspeed, over 40% higher compared ot the default. This could be due to less traffic and possibly overconfidence in less visually restrictive conditions. The average heart rate during night driving increases to 85 bpm, indicating elevated stress possibly due to the increased speed and the challenges of lower visibility. The average breathing rate decreases from 22 breaths per minute in the default scenario to 17 breaths per minute during night driving, which might indicate a calmer respiratory state despite the increased heart rate. This could be a result of concentration or focus required during night driving, which might lead to more controlled breathing.

#### Conclusion
- Speeds are lower in congestion and higher speeds when surrounding vehicles are overspeeding.
- Heart rate and breathing rate are less sensitive to changes in driving conditions, maintaining a relatively stable range across the scenarios. 
- The consistency in heart rate and breathing rate across conditions might suggest that physiological conditions are not heavily affected by external driving conditions, or that the driver is accustomed to these varying conditions.

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
