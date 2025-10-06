// Function to update job stats
async function updateJobStats() {
    try {
        const response = await fetch('/api/job-stats');
        const data = await response.json();
        
        document.getElementById('totalJobs').textContent = data.total_jobs;
        document.getElementById('successfulJobs').textContent = data.successful_jobs;
        document.getElementById('failedJobs').textContent = data.failed_jobs;
        document.getElementById('queuedJobs').textContent = data.queued_jobs;
    } catch (error) {
        console.error('Error updating job stats:', error);
    }
}

// Function to load and display Jenkins jobs
async function loadJenkinsJobs() {
    try {
        const response = await fetch('/api/jobs');
        const jobs = await response.json();
        
        if (Array.isArray(jobs)) {
            const jobsList = document.getElementById('jobsList');
            jobsList.innerHTML = ''; // Clear existing jobs
            
            jobs.forEach(job => {
                const jobElement = document.createElement('div');
                jobElement.className = 'bg-[#004d3a] p-4 rounded-lg border border-[#9bd8b9] mb-4';
                
                const statusColor = job.status === 'SUCCESS' ? 'text-green-400' :
                                  job.status === 'FAILURE' ? 'text-red-400' :
                                  'text-yellow-400';
                
                jobElement.innerHTML = `
                    <div class="flex justify-between items-center">
                        <h3 class="text-lg font-semibold text-white">${job.name}</h3>
                        <span class="${statusColor} font-medium">${job.status || 'UNKNOWN'}</span>
                    </div>
                    <p class="text-[#9bd8b9] text-sm mt-2">${job.description || 'No description'}</p>
                    ${job.last_build_number ? 
                        `<div class="text-sm text-gray-300 mt-2">
                            Build #${job.last_build_number}
                        </div>` : ''
                    }
                    <a href="${job.url}" target="_blank" 
                       class="mt-3 inline-block text-sm text-[#9bd8b9] hover:text-white transition-colors">
                        View in Jenkins →
                    </a>
                `;
                
                jobsList.appendChild(jobElement);
            });
        }
    } catch (error) {
        console.error('Error loading jobs:', error);
    }
}

function startJobStatsUpdates() {
    updateJobStats();  // Initial update
    loadJenkinsJobs(); // Initial jobs load
    setInterval(updateJobStats, 5000);  // Update stats every 5 seconds
    setInterval(loadJenkinsJobs, 30000); // Update jobs list every 30 seconds
}

// Handle login form submission
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            document.querySelector('.min-h-screen').style.display = 'none';
            document.getElementById('dashboard').classList.remove('hidden');
            startJobStatsUpdates();
        } else {
            alert('Invalid credentials');
        }
    } catch (error) {
        alert('Error connecting to server');
    }
});