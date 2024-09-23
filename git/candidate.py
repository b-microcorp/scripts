# Python script to create the candidate using Gitlab API and conventional commit structure
# Assert that requests & gitpython  installed from pip
# The script asserts that all the repositories are located in MASTER_REPO_PATH
# If you want to generate a candidate, ensure that you update USER_ASSIGN_ID to yours
import subprocess
import git
import requests
import datetime
import json 

BRANCH_NAME = datetime.date.today().strftime('%Y-%m-%d') + "_candidate"

GITLAB_HOST = 'GITLAB HOST'
GITLAB_PROJECTS_PATH = GITLAB_HOST + 'api/v4/groups/{id}'
GITLAB_BRANCHES = GITLAB_HOST + 'api/v4/projects/{id}/repository/branches/' + BRANCH_NAME
GITLAB_MR = GITLAB_HOST + 'api/v4/projects/{id}/merge_requests'
TOKEN = 'TOKEN TO GET FROM SECURED SOURCE'
HEADERS = {'PRIVATE-TOKEN': TOKEN, 'Content-Type': 'application/json'}
GROUP_IDS = [12, 19]
USER_ASSIGN_ID = 19

MASTER_REPO_PATH = '/adelya/projects/'

def initMergeRequestData():
    data = {}
    data['source_branch'] = BRANCH_NAME
    data['target_branch'] = 'master'
    data['title'] = BRANCH_NAME
    data['assignee_id'] = USER_ASSIGN_ID
    data['remove_source_branch'] = True
    data['squash'] = False
    data['squash_on_merge'] = False
    return data
    

if __name__ == '__main__':
    print('Starting the candidate...')
    print('>>> Listing repositories...')
    cmd = "find " + MASTER_REPO_PATH + " -type d -exec test -e '{}/.git' ';' -print -prune"
    
    # Step 1: get the repo and push a candidate branch
    data = subprocess.run(cmd ,capture_output=True,shell=True)
    ret = str(data.stdout)[2:-1]
    # Splits data on false new line and remove the last (empty) element
    repositories = [x for x in  ret.split('\\n')[0:-1] if "Plateforme/" in x or "Clients/" in x]
    
    print('>>> Processing each repo...')
    for repo in repositories:
        # format the repo path as it does not work on the POS base
        repoName = repo.split('/')[-1]
        print('    >>> Repo {' + repoName + '}')
        repoPath = repo + '/'
        try:
            r = git.Repo(repoPath)
            r.git.fetch()
            r.git.reset('--hard')
            # Update release
            r.git.checkout('release')
            r.git.reset('--hard')
            r.git.pull()
            releaseBranch = r.active_branch
            # Update master
            r.git.checkout('master')
            r.git.reset('--hard')
            r.git.pull()
            # New branch (candidate)
            candidateBranch = r.create_head(BRANCH_NAME)
            candidateBranch.checkout()
            # Merge & push
            r.git.merge('release')
            r.git.push('--set-upstream', 'origin', candidateBranch)
            releaseBranch.checkout()    
            print('        >>> Candidate branch has been pushed')        
        except Exception as error:
            if 'CONFLICT' in str(error):
                print('        ### Error detected on autmatic merge (release into candidate from master)')
                print('        ### {' + repoName + '} Will not be pushed, and held on local branch. Please fix conflicts, push and create the MR manually.')
            elif "pathspec 'release' did not match" in str(error):
                print('        ??? Ignored: release doest not exist as a branch')
            else:
                print('        XXX Fatal Error detected {' + str(error) + '}')
        
          
    # Step 2: for each project in monolith, ensure that if we have a remote candidate branch, we create the Merge request
    print('>>> Generating merge requests...')
    for groupId in GROUP_IDS: 
        path = GITLAB_PROJECTS_PATH.replace('{id}', str(groupId))
        response = requests.get(url=path, headers=HEADERS)
        data = response.json()
        for project in data['projects']:
            # Checks if the branch exists
            branchUrl = GITLAB_BRANCHES.replace('{id}', str(project['id']))
            existingCandidate = requests.get(url=branchUrl, headers=HEADERS).json()
            if 'message' not in existingCandidate:
                print('    >>>' + project['name'] + '{'+ str(project['id']) + '}: will have a merge request generated')
                # Prepare MR Data
                data = initMergeRequestData()
                # Ok branch found in remote so open the merge request
                if groupId == 19:
                    data['reviewer_ids'] = [0] 
                responseMergeRequest = requests.post(url=GITLAB_MR.replace('{id}', str(project['id'])), headers=HEADERS, json=data)
    print('End candidate generation')
