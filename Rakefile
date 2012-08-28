
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
  tag = "pup-release"
  sh("git tag -f #{tag}")
  sh("git push origin --tags")
end
