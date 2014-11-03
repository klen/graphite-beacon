desc "Build graphite-beacon docker"
task :build do
  sh "docker build -t graphite-beacon . "
end

desc "Run demo docker container"
task :run => :build do
  sh "docker run -v $(pwd)/example-config.json:/etc/config.json graphite-beacon"
end

