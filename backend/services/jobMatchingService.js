const computeCosineSimilarity = require('compute-cosine-similarity');
const parseResume = require("../utils/parser")
const extractResumeSections = require("../utils/extractResumeSections")

const { generateResumeEmbedding } = require("../utils/jina");
const { extractJobsFromDatabase } = require("../scripts/extractJobsFromDatabase")

const matchResumeToJobs = async (filePath, allJobs, jobTitle) => {
  const text = await parseResume(filePath) 
  // const relevantResumeSections = await extractResumeSections(text, jobTitle) 
  /*
  const resumeEmbedding = await generateResumeEmbedding(relevantResumeSections);

  if (!resumeEmbedding) {
    console.error("Failed to generate resume embedding.")
    return []
  } */

  //const jobDataList = await extractJobsFromDatabase()
  /*
  const jobDataList = [
    {'title': 'Software Engineer, Mobile, iOS, Photos', 
    'company': 'Google', 
    'logo_link': 'https://bx-branding-gateway.cloud.seek.com.au/6faea524-c15a-4019-a848-ce1a9c85cb70.1/serpLogo', 
    'description': 'At Google, we have a vision of empowerment and equitable opportunity for all Aboriginal and Torres Strait Islander peoples and commit to building reconciliation through Google’s technology, platforms and people and we welcome Indigenous applicants. Please see our Reconciliation Action Plan for more information.', 
    'responsibilities': ['Write product or system development code.', 'Review code developed by other engineers and provide feedback to ensure best practices.', 'Contribute to existing documentation or educational content and adapt content based on product/program updates and user feedback.', 'Triage product or system issues and debug/track/resolve by analyzing the sources of issues and the impact on hardware, network, or service operations and quality.', 'Participate in, or lead design reviews with peers and stakeholders to decide amongst available technologies.'], 
    'requirements': ['Bachelor’s degree or equivalent practical experience.', '2 years of experience with software development in one or more programming languages, or 1 year of experience with an advanced degree in an industry setting.', '2 years of experience with data structures or algorithms in either an academic or industry setting.', '2 years of experience with iOS application development.', "Master's degree in Computer Science or a related technical field.", '2 years of experience with performance, large scale systems data analysis, visualization tools, or debugging.', 'Experience developing accessible technologies.', 'Proficiency in code and system health, diagnosis and resolution, and software test engineering.'], 
    'location': 'Sydney', 
    'experience_level': 'senior', 
    'salary': '$', 
    'other': ['World Class Benefits', 'Work authorization in Australia required.', 'Indigenous applicants welcome.', 'Perks and benefits: Health & Wellness, Financial Wellbeing, Flexibility & Time Off, Family Support & Care, Community & Personal Development, Googley Extras.'], 
    'posted_date': '22/04/2025', 
    'quick_apply_url': 'https://www.seek.com.au/job/83711517/apply', 
    'job_url': 'https://www.seek.com.au/job/83711517'}, 
    {'title': 'IAM Engineer (Forgerock)', 'company': 'Davidson Recruitment', 'logo_link': 'https://image-service-cdn.seek.com.au/7c6b00bd4a49a35d6488efea1dfe7ebfde3ccac3/1c056a984962480605a20a31bcae496022b57b25', 'description': "We're partnering with a major financial institution seeking multiple experienced IAM Engineers (ForgeRock) to support and enhance its large-scale Customer Identity and Access Management (CIAM) platform.", 'responsibilities': 
      ['Manage and evolve core CIAM services with a strong focus on stability, scalability, and performance.', 'Support the engineering, deployment, and lifecycle management of ForgeRock components (AM, IDM, DS).', 'Work in containerized environments leveraging Kubernetes and Istio for service mesh/orchestration.', 'Apply DevOps practices to automate and enhance CI/CD pipelines, monitoring, and delivery processes.', 'Implement and support secure authentication/authorization protocols including OIDC and OAuth2.'], 'requirements': ['Proven hands-on experience with ForgeRock IAM suite.', 'Skilled in Kubernetes (mandatory), Istio (preferred), and CI/CD tools.', 'Comfortable with secure protocols such as OIDC and OAuth2.', 'Self-starter with the ability to quickly become effective in large, fast-moving enterprise environments.', 'Experience in the banking sector or similarly complex environments is a plus.'], 'location': 'Sydney', 'experience_level': 'junior', 'salary': '$1k - $1100 p.d.', 'other': ['Initial 6-month contract with high potential for extension.', 'Be part of a cutting-edge CIAM transformation within a leading financial institution.', 'Hybrid working environment, with 50% in-office policy across Melbourne, Brisbane or Sydney.', 'Please apply with a current resume in Microsoft Word format only (.doc or .docx).'], 'posted_date': '19/04/2025', 'quick_apply_url': 'https://www.seek.com.au/job/83713030/apply', 
    'job_url': 'https://www.seek.com.au/job/83713030'},
    {'title': 'Senior Azure API Developer', 
    'company': 'Department of Planning, Housing and Infrastructure NSW', 
    'logo_link': 'https://image-service-cdn.seek.com.au/c1fc04f1f5fbf0c04921138f295f1a3591494e53/f3c5292cec0e05e4272d9bf9146f390d366481d0', 
    'description': 'Join our team for a fantastic culture with dynamic collaboration and genuine long-term career support. We offer flexibility in work arrangements, diverse and fulfilling assignments, and prioritize work/life balance and wellbeing with initiatives like flex leave and access to support programs.', 'responsibilities': ['Provide guidance on the design, development, and delivery of end-to-end integration solutions using Azure technologies.', 'Collaborate closely with stakeholders, troubleshoot and optimise solutions, and contribute to business improvements through technical excellence and strong documentation.', 'Work as part of a high-performing team, providing guidance on the design, development, and delivery of end-to-end integration solutions using Azure technologies.'], 
    'requirements': ['Proven experience in developing and delivering integration solutions using the Azure Integration Platform, including API Management, Azure Functions, Logic Apps, and related services.', 'Strong knowledge of API design, implementation, and testing for seamless integration across applications and services.', 'The ability to manage competing priorities while delivering high-quality, reliable solutions within project timelines.', 'Strong problem-solving and analytical skills, with the ability to identify issues and design effective technical solutions.', 'A collaborative approach to working with stakeholders, clients, and cross-functional teams in a complex environment.', 'Resilience and adaptability in navigating change and delivering outcomes in fast-paced settings.', 'Clerk Grade 9/10 Salary relative to experience and ranges from $125,693 to $138,510'], 'location': 'Sydney', 'experience_level': 'senior', 'salary': 'Clerk Grade 9/10 Salary relative to experience and ranges from $125,693 to $138,510 + super', 'other': ['Join our team for a fantastic culture with dynamic collaboration and genuine long-term career support.', 'We offer flexibility in work arrangements, diverse and fulfilling assignments, and prioritize work/life balance and wellbeing with initiatives like flex leave and access to support programs.', 'Temporary full-time opportunity until June 2026 with possibility of extension'], 'posted_date': '1/04/2025', 'quick_apply_url': 'https://www.seek.com.au/job/83714857/apply', 'job_url': 'https://www.seek.com.au/job/83714857'},
    {'title': 'Senior Tariff & Trade Consultant - Customs (SYD/MEL)', 'company': 'Stone Freight Solutions', 'logo_link': 'https://bx-branding-gateway.cloud.seek.com.au/31c1ac2c-745a-7dd0-f9d7-30c545a50932.1/serpLogo', 'description': "Due to continued development and growth this internationally recognised leading software company with platforms for continual investment seeking local industry guru's (Customs Brokers/Consultants) to join team at Head office Alexandria or Melbourne office. (However, some WFH).", 
      'responsibilities': ['You will be reviewing Global Policies and challenging for reform.', 'You are a Licenced Customs Broker who is practicing high level consulting on a daily basis.', 'You will be working with technical and compliance capabilities, competently to review and audit whilst offering your extensive knowledge and experience with harmonised systems, global conventions and agreements.'], 'requirements': ['Senior Tariff and Trade consultant with 10+ years experience', 'Senior Customs broker role with experience in complex matters', 'Licenced Customs Broker', 
      'Strong technical and compliance capabilities and competent to review and audit whilst offering your extensive knowledge and experience with harmonised systems, global conventions and agreements', 'BorderWise and Cargowise1 software sought', 'BorderWise and Cargowise1 required', '10 years of experience in Trade Consultant role', '5 years of experience in Customs Broker role'], 'location': 'Sydney', 'experience_level': 'senior', 'salary': '$140,000 – $180,000 per year ', 'other': ['Excellent salary on offer that will be in accordance with your experience and value.', 
      'Newly created opportunities looking for the best of the best to join adding experience and value from your skillset.'], 'posted_date': '23/04/2025', 'quick_apply_url': 'https://www.seek.com.au/job/83712062/apply', 'job_url': 'https://www.seek.com.au/job/83712062'}
  ] 
  */
  // Create an array of jobs with their cosine similarity to the resume 
  /*const jobSimilarities = jobDataList.map((job) => {
    const jobEmbedding = job.embedding  // Assuming the job embedding is already stored
    if (!jobEmbedding) {
      return { job, similarity: -1 }
    }
    const similarity = computeCosineSimilarity(resumeEmbedding, jobEmbedding)
    return { job, similarity }
  })
  // Sort the jobs by similarity (highest to lowest)
  const sortedJobs = jobSimilarities.sort((a, b) => b.similarity - a.similarity)
  // Return the sorted list of jobs
  return sortedJobs.map(item => item.job)  */
  return allJobs;
  
}

module.exports = { matchResumeToJobs }

