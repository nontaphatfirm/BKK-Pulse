# Data Science Project (2026/1) (15%) — Bangkok CCTV Image Analysis

**Course:** 2110403 Data Science and Data Engineering (DSDE-CEDT)

| Milestone | Date |
| --- | --- |
| Release date | Tue 3 Nov 2026 |
| Student group submission in MCV | Sun 15 Nov 2026 |
| Package submission deadline | Sun 6 Dec 2026 |

> Converted from [`2110403_2026s1_Project_CEDT.pdf`](./2110403_2026s1_Project_CEDT.pdf).

## Objective

- Data science is a discipline focused on extracting insights from data through processes such as data preparation, analysis, visualization, and modeling.
- However, one common challenge in real-world data science projects is obtaining usable data. While many tutorial datasets are already provided in structured formats, real-world data is often unstructured and messy.
- In this project, traffic camera data was scraped from the Bangkok Metropolitan Administration (BMA) Traffic platform as raw images.
- Therefore, the objective of this project is to design a practical workflow that transforms raw Bangkok CCTV images into structured data, analyzes meaningful spatial and/or temporal patterns, and presents the resulting insights through an analytical dashboard.

## Bangkok CCTV Image Dataset

Full raw Bangkok CCTV images collected from 100 CCTV camera locations.

- Data was collected from **100 CCTV camera locations**.
- The number of images is highly consistent across the 100 selected cameras, with approximately **604–631 images per camera**.
- CCTV images are captured under diverse and uncontrolled conditions, including different camera angles, road layouts, traffic densities, and backgrounds.
- Image quality also varies with time of day and lighting conditions, such as low light, glare, shadows, and reflections from wet roads.
- **Dataset link:** <https://drive.google.com/drive/folders/1k2-KxXe4wbDmFGcGXI-pK7TdSXjBHTni?usp=sharing>

![Locations of the 100 selected CCTV cameras in Bangkok](assets/page3-camera-map.jpg)

CCTV images are captured under diverse and uncontrolled conditions, including different camera angles, road layouts, traffic densities, and backgrounds.

![Diverse camera angles, road layouts, traffic densities, and backgrounds](assets/page4-diverse-conditions.jpg)

Image quality also varies with time of day and lighting conditions, such as low light, glare, shadows, and reflections from wet roads.

![Varied lighting: low light, glare, shadows, and wet-road reflections](assets/page5-lighting-conditions.jpg)

## Project Criteria

- Each group can have up to **6 members** (maximum).
- The project should demonstrate an end-to-end data science workflow that delivers practical applications or meaningful insights. Full automation is not required, but the project must include at least the following **4 components**:

### Component 1: Data Engineering

- This should also include data cleansing and data preparation.
- Workflow management can be considered part of data engineering, so it would be great if you could make the entire process run end-to-end.
- **Note:** Web scraping cannot be counted since it is a required task.

### Component 2: Data Science

- This component applies analytical methods to explore patterns, trends, and insights from the prepared dataset.

### Component 3: BI Dashboard

### Component 4: The Outcome of Your Analysis (Insights)

Ensuring the quality of the data processing workflow, adding additional components, or providing deeper analysis will enhance the project's depth and may lead to additional points.

## Required Task: Additional Data Collection via Web Scraping

Since web scraping is an important skill in data science, each group must collect additional data to make your analysis more interesting and insightful.

1. **Simple web scraping / APIs:** Collect data from at least **3 additional data sources**.
2. **Interactive websites:** If scraping requires advanced tools such as Playwright, Selenium, or Crawlee, collecting data from **1 additional data source** is sufficient.

This data collection is a separate task and **does not count toward the Data Engineering (DE) module**. Integrating multiple relevant data sources can make your project more compelling and may earn extra points.

## Scoring Criteria (15%)

### Part 1: Implementation (10%)

The scoring criteria will be based on:

- **Completeness:** Ensuring all required components + web scraping.
- **Project interestingness:** Evaluated through:
  - Effort (e.g., incorporating additional data)
  - Execution
  - Technical quality
  - Other relevant factors

### Part 2: Submission Package (5%)

#### Presentation Video

- Upload the video to YouTube and set it **unlisted or public**. The video should be shared in the project channel on Discord by the deadline for other groups to view.
- The video length is **15 minutes**, where the presentation quality will be a key factor in evaluation.
- The video should include:
  1. An explanation of the data used, including any additional data sources if applicable.
  2. A breakdown of each of the required components, with a diagram illustrating how they interconnect, and your analysis results.
  3. A demo showcasing interesting results from your data analysis.

#### Other Deliverables

- Source code and presentation slides (PDF).
- Submission should include a link to a Google Drive folder shared on myCourseVille with **"viewer" access for anyone**.

## Important Remarks

- Create the student group in MCV by **Sun 15 Nov 2026** (maximum 6 students).
- Submit your project via MyCourseVille by the stated deadline (**Sun 6 Dec 2026**). Late submissions will incur a score reduction.
- Ensure that your YouTube and Google Drive links are both accessible. If we can't open them, your work will receive a **score of 0**.
- Don't forget to share it in the Discord channel **#project-showroom**, along with a short description of your project.

## FAQ

_(No FAQ content in the source docuent.)_
