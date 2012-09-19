
desc "Run tests"
task "test" do
  sh("nosetests")
end

desc "Run dogstatsd tests"
task "test:dogstatsd" do
  sh("nosetests tests/test_dogstatsd.py")
end

desc "Run the agent locally"
task "run" do
  sh("supervisord -n -c supervisord.dev.conf")
end

desc "Update pup release tag to the current commit"
task "pup:tag" do
  # This is an abomination. We distributed our install pup script via bitly
  # (which can't change) which is hardcoded to a github url (add-pup). Matt
  # Perpick made this worse by trying to change it and adding another one
  # (pup-release). We can't do anything about this now, because both links are
  # in the wild.
  tag = "pup-release"
  sh("git tag -f #{tag}")
  sh("git push origin --tags")
  sh("git co add-pup && git merge pup-release")
  sh("git push origin add-pup")
end

task :default => [:test]

